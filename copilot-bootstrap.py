#!/usr/bin/env python

from collections import defaultdict
from pathlib import Path
import re
import sys

import boto3
import click
from cloudfoundry_client.client import CloudFoundryClient
import jinja2
from schema import Optional, Schema, SchemaError
import yaml


SSM_BASE_PATH = "/copilot/{app}/{env}/secrets/"
SSM_PATH = "/copilot/{app}/{env}/secrets/{name}"


config_schema = Schema({
    "app": str,
    "domain": str,
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
            "command": str,
            Optional("notes"): str,
            Optional("secrets_from"): str,
            "environments": {
                str: {
                    "paas": str,
                    Optional("url"): str,
                    Optional("ipfilter"): bool,
                }
            },
            "backing-services": [
                {
                    "name": str,
                    "type": lambda s: s in ("s3", "external-s3", "postgres", "redis", "opensearch",),
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


def _mkdir(base, path):

    if (base / path).exists():
        return f"directory {path} exists; doing nothing"

    (base / path).mkdir(parents=True)
    return f"directory {path} created"


def _mkfile(base, path, contents):

    if (base / path).exists():
        return f"file {path} exists; doing nothing"

    with open(base / path, "w") as fd:
        fd.write(contents)
    return f"file {path} created"


def camel_case(s):
    s = re.sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return ''.join([s[0].lower(), s[1:]])


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


def get_template_env():
    template_path = Path(__file__).parent / Path("templates")
    templateLoader = jinja2.FileSystemLoader(searchpath=template_path)
    templateEnv = jinja2.Environment(loader=templateLoader)

    return templateEnv


def load_and_validate_config(path):

    with open(path, "r") as fd:
        conf = yaml.safe_load(fd)

    # validate the file
    schema = Schema(config_schema)
    config = schema.validate(conf)

    return config


def set_ssm_param(app, env, param_name, param_value, overwrite, exists):
    client = boto3.client('ssm')
    args = dict(
        Name=param_name,
        Description='copied from cloudfoundry',
        Value=param_value,
        Type='SecureString',
        Overwrite=overwrite,
        Tags=[
                {
                    'Key': 'copilot-application',
                    'Value': app
                },
                {
                    'Key': 'copilot-environment',
                    'Value': env
                },
        ],
    )

    if overwrite and exists:
        # Tags can't be updated when overwriting
        del args["Tags"]

    response = client.put_parameter(**args)


def get_ssm_secret_names(app, env):
    client = boto3.client('ssm')

    path = SSM_BASE_PATH.format(app=app, env=env)

    params = dict(
        Path=path,
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    secret_names = []

    while True:
        response = client.get_parameters_by_path(
            **params
        )

        for secret in response["Parameters"]:
            # secret_names.append(secret["Name"].split("/")[-1])
            secret_names.append(secret["Name"])

        if "NextToken" in response:
            params["NextToken"] = response["NextToken"]
        else:
            break

    return sorted(secret_names)


@click.group()
def cli():
    pass


@cli.command()
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

    templateEnv = get_template_env()

    env_template = templateEnv.get_template("env-manifest.yml")
    instructions_template = templateEnv.get_template("instructions.txt")

    backing_service_templates = {
        "opensearch": templateEnv.get_template("addons/opensearch.yml"),
        "postgres": templateEnv.get_template("addons/postgres.yml"),
        "redis": templateEnv.get_template("addons/redis.yml"),
        "s3": templateEnv.get_template("addons/s3.yml"),
        "external-s3": templateEnv.get_template("addons/external-s3.yml"),
    }

    service_templates = {
        "public": templateEnv.get_template("svc-manifest-public.yml"),
        "backend": templateEnv.get_template("svc-manifest-backend.yml"),
    }

    click.echo("GENERATING COPILOT CONFIG FILES")

    # create copilot directory
    click.echo(_mkdir(base_path, "copilot"))

    # create copilot/.workspace file
    contents = "application: {}".format(config["app"])
    click.echo(_mkfile(base_path, "copilot/.workspace", contents))

    # create copilot/environments directory
    click.echo(_mkdir(base_path, "copilot/environments"))

    # create each environment diretory and manifest.yml
    for name, env in config["environments"].items():
        click.echo(_mkdir(base_path, f"copilot/environments/{name}"))
        contents = env_template.render({
            "name": name,
            "certificate_arn": env["certificate_arns"][0] if "certificate_arns" in env else ""
        })
        click.echo(_mkfile(base_path, f"copilot/environments/{name}/manifest.yml", contents))

    # create each service directory and manifest.yml
    for service in config["services"]:
        service["ipfilter"] = any(env.get("ipfilter", False) for _, env in service["environments"].items())
        name = service["name"]
        click.echo(_mkdir(base_path, f"copilot/{name}/addons/"))

        if "secrets_from" in service:
            # Copy secrets from the app referredd to in the "secrets_from" key
            related_service = [s for s in config["services"] if s["name"] == service["secrets_from"]][0]

            service["secrets"].update(related_service["secrets"])

        contents = service_templates[service["type"]].render(service)

        click.echo(_mkfile(base_path, f"copilot/{name}/manifest.yml", contents))

        if service["backing-services"]:
            click.echo(_mkdir(base_path, "copilot"))

        for bs in service["backing-services"]:
            bs["prefix"] = camel_case(name + "-" + bs["name"])

            contents = backing_service_templates[bs["type"]].render(dict(service=bs))
            _mkfile(base_path, f"copilot/{name}/addons/{bs['name']}.yml", contents)

    # generate instructions
    config["config_file"] = config_file
    instructions = instructions_template.render(config)
    click.echo("---")
    click.echo(instructions)


@cli.command()
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


@cli.command()
@click.argument("config-file", type=click.Path(exists=True))
def instructions(config_file):
    """
    Show migration instructions
    """
    templateEnv = get_template_env()

    config = load_and_validate_config(config_file)
    config["config_file"] = config_file

    instructions_template = templateEnv.get_template("instructions.txt")
    instructions = instructions_template.render(config)

    click.echo(instructions)


if __name__ == "__main__":
    cli()
