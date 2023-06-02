#!/usr/bin/env python

import copy
import json
from pathlib import Path

import boto3
import click
from jsonschema import validate as validate_json
import yaml

from .utils import camel_case, mkdir, mkfile, SSM_BASE_PATH, setup_templates


BASE_DIR = Path(__file__).parent.parent


@click.group()
def copilot():
    pass


def _validate_and_normalise_config(config_file):
    """Load the storage.yaml file, validate it and return the normalised config dict"""

    def _lookup_plan(storage_type, env_conf):
        plan = env_conf.pop("plan", None)
        conf = storage_plans[storage_type][plan] if plan else {}
        conf.update(env_conf)

        return conf

    def _normalise_keys(source: dict):
        return {k.replace("-", "_"): v for k, v in source.items()}

    with open(BASE_DIR / "storage-plans.yaml", "r") as fd:
        storage_plans = yaml.safe_load(fd)

    with open(BASE_DIR / "schemas/storage-schema.json", "r") as fd:
        schema = json.load(fd)

    # load and validate config
    with open(config_file, "r") as fd:
        config = yaml.safe_load(fd)

    validate_json(instance=config, schema=schema)

    env_names = [path.parent.parts[-1] for path in Path("./copilot/environments/").glob("*/manifest.yml")]
    svc_names = [path.parent.parts[-1] for path in Path("./copilot/").glob("*/manifest.yml")]

    if not env_names:
        click.echo(click.style(f"No environments found in ./copilot/environments; exiting", fg="red"))
        exit(1)

    if not svc_names:
        click.echo(click.style(f"No services found in ./copilot/; exiting", fg="red"))
        exit(1)

    normalised_config = {}
    for storage_name, storage_config in config.items():
        storage_type = storage_config["type"]
        normalised_config[storage_name] = copy.deepcopy(storage_config)

        if "services" in normalised_config[storage_name]:
            valid_services = [svc for svc in normalised_config[storage_name]["services"] if svc in svc_names]
            if valid_services != normalised_config[storage_name]["services"]:
                normalised_config[storage_name]["services"] = valid_services
                click.echo(click.style(f"Services listed in {storage_name} do not exist in ./copilot/", fg="red"))

        environments = normalised_config[storage_name].pop("environments", {})
        default = environments.pop("default", {})

        initial = _lookup_plan(storage_type, default)

        normalised_environments = {}

        for env in env_names:
            normalised_environments[env] = _normalise_keys(initial)

        for env_name, env_config in environments.items():
            if env_name not in normalised_environments:
                click.echo(click.style(f"Environment key {env_name} listed in {storage_name} does not exist in ./copilot/environments", fg="red"))
            else:
                normalised_environments[env_name].update(
                    _lookup_plan(storage_type, _normalise_keys(env_config))
                )

        normalised_config[storage_name]["environments"] = normalised_environments

    return normalised_config


@copilot.command()
@click.argument("storage-config-file", type=click.Path(exists=True))
@click.argument("output", type=click.Path(exists=True), default=".")
@click.option('--overwrite', is_flag=True, show_default=True, default=True, help='Overwrite existing cloudformation? Defaults to True')
def make_cloudformation(storage_config_file, output, overwrite):
    """
    Generate storage cloudformation for each environment
    """

    templates = setup_templates()

    if not Path("./copilot").exists() or not Path("./copilot").is_dir():
        click.echo("Cannot find copilot directory. Run this command in the root of the deployment repository.")

    config = _validate_and_normalise_config(storage_config_file)

    click.echo("\n>>> Generating cloudformation\n")

    path = Path(f"copilot/environments/addons/")
    click.echo(mkdir(output, path))

    services = []
    for storage_name, storage_config in config.items():
        storage_type = storage_config.pop("type")
        environments = storage_config.pop("environments")

        service = {
            "secret_name": storage_name.upper().replace("-", "_"),
            "name": storage_config.get("name", None) or storage_name,
            "environments": environments,
            "prefix": camel_case(storage_name),
            "storage_type": storage_type,
            **storage_config,
        }

        services.append(service)

        # s3-policy only applies to individual services
        if storage_type != "s3-policy":
            template = templates["env"][storage_type]
            contents = template.render({
                "service": service
            })

            click.echo(mkfile(output, path / f"{storage_name}.yml", contents, overwrite=overwrite))

        # s3 buckets require additional service level cloudformation to grant the ECS task role access to the bucket
        if storage_type in ["s3", "s3-policy"]:

            template = templates["svc"]["s3-policy"]

            for svc in storage_config.get("services", []):

                path = Path(f"copilot/{svc}/addons/")

                service = {
                    "name": storage_config.get("name", None) or storage_name,
                    "prefix": camel_case(storage_name),
                    "environments": environments,
                    **storage_config,
                }

                contents = template.render({
                    "service": service
                })

                click.echo(mkdir(output, path))
                click.echo(mkfile(output, path / f"{storage_name}.yml", contents, overwrite=overwrite))

    click.echo(templates["storage-instructions"].render(services=services))


@copilot.command()
@click.argument("service_name", type=str)
@click.argument("env", type=str, default="prod")
def get_service_secrets(service_name, env):
    """
    List secret names and values for a service
    """

    if not Path("./copilot").exists() or not Path("./copilot").is_dir():
        click.echo("Cannot find copilot directory. Run this command in the root of the deployment repository.")

    client = boto3.client('ssm')

    path = SSM_BASE_PATH.format(app=service_name, env=env)

    params = dict(
        Path=path,
        Recursive=False,
        WithDecryption=True,
        MaxResults=10
    )
    secrets = []

    # TODO: refactor shared code with get_ssm_secret_names
    while True:
        response = client.get_parameters_by_path(
            **params
        )

        for secret in response["Parameters"]:
            secrets.append("{:<8}: {:<15}".format(secret["Name"], secret["Value"]))

        if "NextToken" in response:
            params["NextToken"] = response["NextToken"]
        else:
            break

    print("\n".join(sorted(secrets)))


if __name__ == "__main__":
    copilot()
