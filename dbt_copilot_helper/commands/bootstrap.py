#!/usr/bin/env python

from collections import defaultdict
from pathlib import Path

import click
import yaml
from botocore.exceptions import ClientError
from cloudfoundry_client.client import CloudFoundryClient
from schema import Optional
from schema import Or
from schema import Schema

from dbt_copilot_helper.utils.aws import SSM_PATH
from dbt_copilot_helper.utils.aws import check_aws_conn
from dbt_copilot_helper.utils.aws import get_ssm_secret_names
from dbt_copilot_helper.utils.aws import get_ssm_secrets
from dbt_copilot_helper.utils.aws import set_ssm_param
from dbt_copilot_helper.utils.click import ClickDocOptGroup
from dbt_copilot_helper.utils.files import mkdir
from dbt_copilot_helper.utils.files import mkfile
from dbt_copilot_helper.utils.template import setup_templates
from dbt_copilot_helper.utils.validation import validate_string
from dbt_copilot_helper.utils.versioning import (
    check_copilot_helper_version_needs_update,
)

range_validator = validate_string(r"^\d+-\d+$")
seconds_validator = validate_string(r"^\d+s$")

config_schema = Schema(
    {
        "app": str,
        "environments": {str: {Optional("certificate_arns"): [str]}},
        "services": [
            {
                "name": str,
                "type": lambda s: s
                in (
                    "public",
                    "backend",
                ),
                "repo": str,
                "image_location": str,
                Optional("notes"): str,
                Optional("secrets_from"): str,
                "environments": {
                    str: {
                        "paas": str,
                        Optional("url"): str,
                        Optional("ipfilter"): bool,
                        Optional("memory"): int,
                        Optional("count"): Or(
                            int,
                            {  # https://aws.github.io/copilot-cli/docs/manifest/lb-web-service/#count
                                "range": range_validator,  # e.g. 1-10
                                Optional("cooldown"): {
                                    "in": seconds_validator,  # e.g 30s
                                    "out": seconds_validator,  # e.g 30s
                                },
                                Optional("cpu_percentage"): int,
                                Optional("memory_percentage"): Or(
                                    int,
                                    {
                                        "value": int,
                                        "cooldown": {
                                            "in": seconds_validator,  # e.g. 80s
                                            "out": seconds_validator,  # e.g 160s
                                        },
                                    },
                                ),
                                Optional("requests"): int,
                                Optional("response_time"): seconds_validator,  # e.g. 2s
                            },
                        ),
                    },
                },
                Optional("backing-services"): [
                    {
                        "name": str,
                        "type": lambda s: s
                        in (
                            "s3",
                            "s3-policy",
                            "aurora-postgres",
                            "rds-postgres",
                            "redis",
                            "opensearch",
                        ),
                        Optional("paas-description"): str,
                        Optional("paas-instance"): str,
                        Optional("notes"): str,
                        Optional("bucket_name"): str,  # for external-s3 type
                        Optional("readonly"): bool,  # for external-s3 type
                        Optional("shared"): bool,
                    },
                ],
                Optional("overlapping_secrets"): [str],
                "secrets": {
                    Optional(str): str,
                },
                "env_vars": {
                    Optional(str): str,
                },
            },
        ],
    },
)


def secret_should_be_skipped(secret_name):
    return "AWS_" in secret_name


def get_paas_env_vars(client: CloudFoundryClient, paas: str) -> dict:
    org, space, app = paas.split("/")

    env_vars = None

    for paas_org in client.v2.organizations:
        if paas_org["entity"]["name"] == org:
            for paas_space in paas_org.spaces():
                if paas_space["entity"]["name"] == space:
                    for paas_app in paas_space.apps():
                        if paas_app["entity"]["name"] == app:
                            env_vars = paas_app["entity"]["environment_json"]

    if not env_vars:
        raise Exception(f"Application {paas} not found")

    return dict(env_vars)


def load_and_validate_config(path):
    with open(path, "r") as fd:
        conf = yaml.safe_load(fd)

    # validate the file
    schema = Schema(config_schema)
    schema.validate(conf)

    return conf


def to_yaml(value):
    return yaml.dump(value, sort_keys=False)


@click.group(chain=True, cls=ClickDocOptGroup)
def bootstrap():
    check_copilot_helper_version_needs_update()


@bootstrap.command()
@click.option("-d", "--directory", type=str, default=".")
def make_config(directory="."):
    """Generate Copilot boilerplate code."""

    base_path = Path(directory)
    config = load_and_validate_config("bootstrap.yml")

    templates = setup_templates()
    templates.filters["to_yaml"] = to_yaml

    click.echo(">>> Generating Copilot configuration files\n")

    # create copilot directory
    mkdir(base_path, "copilot")

    # create copilot/.workspace file
    contents = f"application: {config['app']}"
    click.echo(mkfile(base_path, "copilot/.workspace", contents))

    # create copilot/environments directory
    mkdir(base_path, "copilot/environments")

    # create each environment directory and manifest.yml
    for name, env in config["environments"].items():
        mkdir(base_path, f"copilot/environments/{name}")
        contents = templates.get_template("env/manifest.yml").render(
            {
                "name": name,
                "certificate_arn": env["certificate_arns"][0] if "certificate_arns" in env else "",
            },
        )
        click.echo(mkfile(base_path, f"copilot/environments/{name}/manifest.yml", contents))

    # create each service directory and manifest.yml
    for service in config["services"]:
        service["ipfilter"] = any(
            env.get("ipfilter", False) for _, env in service["environments"].items()
        )
        name = service["name"]
        mkdir(base_path, f"copilot/{name}/addons/")

        if "secrets_from" in service:
            # Copy secrets from the app referred to in the "secrets_from" key
            related_service = [
                s for s in config["services"] if s["name"] == service["secrets_from"]
            ][0]

            service["secrets"].update(related_service["secrets"])

        contents = templates.get_template(f"svc/manifest-{service['type']}.yml").render(service)

        click.echo(mkfile(base_path, f"copilot/{name}/manifest.yml", contents))

    # link to GitHub docs
    click.echo(
        "\nGitHub documentation: "
        "https://github.com/uktrade/platform-documentation/blob/main/gov-pass-to-copilot-migration",
    )


@bootstrap.command()
@click.option("--project-profile", required=True, help="AWS account profile name")
@click.option("--env", help="Migrate secrets from a specific environment")
@click.option("--svc", help="Migrate secrets from a specific service")
@click.option(
    "--overwrite",
    is_flag=True,
    show_default=True,
    default=False,
    help="Overwrite existing secrets?",
)
@click.option("--dry-run", is_flag=True, show_default=True, default=False, help="dry run")
def migrate_secrets(project_profile, env, svc, overwrite, dry_run):
    """
    Migrate secrets from your GOV.UK PaaS application to DBT PaaS.

    You need to be authenticated via Cloud Foundry CLI and the AWS CLI to use this command.

    If you're using AWS profiles, use the AWS_PROFILE environment variable to indicate the which
    profile to use, e.g.:

    AWS_PROFILE=myaccount copilot-bootstrap.py ...
    """

    check_aws_conn(project_profile)
    # TODO: optional SSM or secret manager

    cf_client = CloudFoundryClient.build_from_cf_config()
    config_file = "bootstrap.yml"
    config = load_and_validate_config(config_file)

    if env and env not in config["environments"].keys():
        raise click.ClickException(f"{env} is not an environment in {config_file}")

    if svc and svc not in [service["name"] for service in config["services"]]:
        raise click.ClickException(f"{svc} is not a service in {config_file}")

    existing_ssm_data = defaultdict(list)
    for env_name, _ in config["environments"].items():
        if env and env_name != env:
            continue

        existing_ssm_data[env_name] = get_ssm_secret_names(config["app"], env_name)

    # get the secrets from the paas
    for service in config["services"]:
        service_name = service["name"]
        secrets = service["secrets"]

        if svc and service["name"] != svc:
            continue

        if "secrets_from" in service:
            click.echo(f"{service_name} shares secrets with {service['secrets_from']}; skipping")
            continue

        for env_name, environment in service["environments"].items():
            if env and env_name != env:
                continue

            click.echo("-----------------")
            click.echo(
                f">>> migrating secrets for service: {service_name}; environment: {env_name}"
            )

            click.echo(f"getting env vars for from {environment['paas']}")
            env_vars = get_paas_env_vars(cf_client, environment["paas"])

            click.echo("Transfering secrets ...")
            for app_secret_key, ssm_secret_key in secrets.items():
                if secret_should_be_skipped(app_secret_key):
                    continue

                ssm_path = SSM_PATH.format(app=config["app"], env=env_name, name=ssm_secret_key)

                if app_secret_key not in env_vars:
                    # NOT FOUND
                    param_value = "NOT FOUND"
                    click.echo(
                        f"Key not found in paas app: {app_secret_key}; setting to 'NOT FOUND'"
                    )
                elif not env_vars[app_secret_key]:
                    # FOUND BUT EMPTY STRING
                    param_value = "EMPTY"
                    click.echo(
                        f"Empty env var in paas app: {app_secret_key}; SSM requires a non-empty string; setting to 'EMPTY'",
                    )
                else:
                    param_value = env_vars[app_secret_key]

                param_exists = ssm_path in existing_ssm_data[env_name]

                if overwrite or not param_exists:
                    if not dry_run:
                        set_ssm_param(
                            config["app"], env_name, ssm_path, param_value, overwrite, param_exists
                        )

                    if not param_exists:
                        existing_ssm_data[env_name].append(ssm_path)

                if not dry_run:
                    text = (
                        "Created"
                        if not param_exists
                        else "Overwritten"
                        if overwrite
                        else "NOT overwritten"
                    )
                    click.echo(f"{text} {ssm_path}")
                else:
                    click.echo(f"{ssm_path} not created because `--dry-run` flag was included.")


@bootstrap.command()
@click.argument("source_environment")
@click.argument("target_environment")
@click.option("--project-profile", required=True, help="AWS account profile name")
def copy_secrets(project_profile, source_environment, target_environment):
    """Copy secrets from one environment to a new environment."""
    check_aws_conn(project_profile)

    if not Path(f"copilot/environments/{target_environment}").exists():
        click.echo(f"""Target environment manifest for "{target_environment}" does not exist.""")
        exit(1)

    config_file = "bootstrap.yml"
    config = load_and_validate_config(config_file)
    secrets = get_ssm_secrets(config["app"], source_environment)

    for secret in secrets:
        secret_name = secret[0].replace(f"/{source_environment}/", f"/{target_environment}/")

        if secret_should_be_skipped(secret_name):
            continue

        click.echo(secret_name)

        try:
            set_ssm_param(
                config["app"],
                target_environment,
                secret_name,
                secret[1],
                False,
                False,
                f"Copied from {source_environment} environment.",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ParameterAlreadyExists":
                click.secho(
                    f"""The "{secret_name.split("/")[-1]}" parameter already exists for the "{target_environment}" environment.""",
                    fg="yellow",
                )
            else:
                raise e


if __name__ == "__main__":
    bootstrap()
