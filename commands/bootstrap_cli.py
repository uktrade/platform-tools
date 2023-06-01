#!/usr/bin/env python

from collections import defaultdict
from pathlib import Path

import click
from cloudfoundry_client.client import CloudFoundryClient
from schema import Optional, Schema
import yaml

from .utils import camel_case, get_ssm_secret_names, mkdir, mkfile, set_ssm_param, SSM_PATH, setup_templates


config_schema = Schema({
    "app": str,
    "environments": {
        str: {
            Optional("certificate_arns"): [str]
        }
    },
    "services": [
        {
            "name": str,
            "type": lambda s: s in ("public", "backend",),
            "repo": str,
            "image_location": str,
            Optional("notes"): str,
            Optional("secrets_from"): str,
            "environments": {
                str: {
                    "paas": str,
                    Optional("url"): str,
                    Optional("ipfilter"): bool,
                }
            },
            Optional("backing-services"): [
                {
                    "name": str,
                    "type": lambda s: s in ("s3", "s3-policy", "aurora-postgres", "rds-postgres", "redis", "opensearch",),
                    Optional("paas-description"): str,
                    Optional("paas-instance"): str,
                    Optional("notes"): str,
                    Optional("bucket_name"): str,           # for external-s3 type
                    Optional("readonly"): bool,             # for external-s3 type
                    Optional("shared"): bool,
                }
            ],
            Optional("overlapping_secrets"): [ str ],
            "secrets": {
                Optional(str): str,
            },
            "env_vars": {
                Optional(str): str,
            },
        }
    ],
})


def get_paas_env_vars(client, paas):

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
    config = schema.validate(conf)

    return config


@click.group()
def bootstrap():
    pass


@bootstrap.command()
@click.argument("config-file", type=click.Path(exists=True))
@click.argument("output", type=click.Path(exists=True), default=".")
def make_config(config_file, output):
    """
    Generate copilot boilerplate code

    CONFIG-FILE is the path to the input yaml config file
    OUTPUT is the location of the repo root dir. Defaults to the current directory.
    """

    base_path = Path(output)
    config = load_and_validate_config(config_file)

    templates = setup_templates()

    click.echo(">>> Generating Copilot configuration files\n")

    # create copilot directory
    click.echo(mkdir(base_path, "copilot"))

    # create copilot/.workspace file
    contents = "application: {}".format(config["app"])
    click.echo(mkfile(base_path, "copilot/.workspace", contents))

    # create copilot/environments directory
    click.echo(mkdir(base_path, "copilot/environments"))

    # create each environment directory and manifest.yml
    for name, env in config["environments"].items():
        click.echo(mkdir(base_path, f"copilot/environments/{name}"))
        contents = templates["env"]["manifest"].render({
            "name": name,
            "certificate_arn": env["certificate_arns"][0] if "certificate_arns" in env else ""
        })
        click.echo(mkfile(base_path, f"copilot/environments/{name}/manifest.yml", contents))

    # create each service directory and manifest.yml
    for service in config["services"]:
        service["ipfilter"] = any(env.get("ipfilter", False) for _, env in service["environments"].items())
        name = service["name"]
        click.echo(mkdir(base_path, f"copilot/{name}/addons/"))

        if "secrets_from" in service:
            # Copy secrets from the app referredd to in the "secrets_from" key
            related_service = [s for s in config["services"] if s["name"] == service["secrets_from"]][0]

            service["secrets"].update(related_service["secrets"])

        contents = templates["svc"][service["type"] + "-manifest"].render(service)

        click.echo(mkfile(base_path, f"copilot/{name}/manifest.yml", contents))

        for bs in service.get("backing-services", []):
            bs["prefix"] = camel_case(name + "-" + bs["name"])

            contents = templates["svc"][bs["type"]].render(dict(service=bs))
            mkfile(base_path, f"copilot/{name}/addons/{bs['name']}.yml", contents)

    # link to GitHub docs
    click.echo("\nGitHub documentation: "
               "https://github.com/uktrade/platform-documentation/blob/main/gov-pass-to-copiltot-migration")


@bootstrap.command()
@click.argument("config-file", type=click.Path(exists=True))
@click.option('--env', help='Migrate secrets from a specific environment')
@click.option('--svc', help='Migrate secrets from a specific service')
@click.option('--overwrite', is_flag=True, show_default=True, default=False, help='Overwrite existing secrets?')
@click.option('--dry-run', is_flag=True, show_default=True, default=False, help='dry run')
def migrate_secrets(config_file, env, svc, overwrite, dry_run):
    """
    Migrate secrets from your gov paas application to AWS/copilot

    You need to be authenticated via cf cli and the AWS cli to use this commmand.

    If you're using AWS profiles, use the AWS_PROFILE env var to indicate the which profile to use, e.g.:

    AWS_PROFILE=myaccount copilot-bootstrap.py ...
    """

    # TODO: optional SSM or secret manager

    cf_client = CloudFoundryClient.build_from_cf_config()
    config = load_and_validate_config(config_file)

    if env and env not in config["environments"].keys():
        raise click.ClickException(f"{env} is not an environment in {config_file}")

    if svc and svc not in config["services"].keys():
        raise click.ClickException(f"{svc} is not a servuce in {config_file}")

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
            click.echo(f">>> migrating secrets fro service: {service_name}; environment: {env_name}")

            click.echo(f"getting env vars for from {environment['paas']}")
            env_vars = get_paas_env_vars(cf_client, environment["paas"])

            click.echo("Transfering secrets ...")
            for app_secret_key, ssm_secret_key in secrets.items():
                ssm_path = SSM_PATH.format(app=config["app"], env=env_name, name=ssm_secret_key)

                if app_secret_key not in env_vars:
                    # NOT FOUND
                    param_value = "NOT FOUND"
                    click.echo(f"Key not found in paas app: {app_secret_key}; setting to 'NOT FOUND'")
                elif not env_vars[app_secret_key]:
                    # FOUND BUT EMPTY STRING
                    param_value = "EMPTY"
                    click.echo(f"Empty env var in paas app: {app_secret_key}; SSM requires a non-empty string; setting to 'EMPTY'")
                else:
                    param_value = env_vars[app_secret_key]

                param_exists = ssm_path in existing_ssm_data[env_name]

                if overwrite or not param_exists:
                    if not dry_run:
                        set_ssm_param(config["app"], env_name, ssm_path, param_value, overwrite, param_exists)

                    if not param_exists:
                        existing_ssm_data[env_name].append(ssm_path)

                text = "Created" if not param_exists else "Overwritten" if overwrite else "NOT overwritten"

                click.echo(f"{text} {ssm_path}")


@bootstrap.command()
@click.argument("config-file", type=click.Path(exists=True))
def instructions(config_file):
    """
    Show migration instructions
    """
    templates = setup_templates()

    config = load_and_validate_config(config_file)
    config["config_file"] = config_file

    instructions = templates["instructions"].render(config)

    click.echo(instructions)


if __name__ == "__main__":
    bootstrap()
