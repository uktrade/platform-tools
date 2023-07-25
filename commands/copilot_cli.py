#!/usr/bin/env python

import copy
import json
from pathlib import Path

import boto3
import click
import yaml
from jsonschema import validate as validate_json

from .utils import SSM_BASE_PATH
from .utils import camel_case
from .utils import ensure_cwd_is_repo_root
from .utils import mkdir
from .utils import mkfile
from .utils import setup_templates

PACKAGE_DIR = Path(__file__).resolve().parent

WAF_ACL_ARN_KEY = "waf-acl-arn"


def list_copilot_local_environments():
    return [path.parent.parts[-1] for path in Path("./copilot/environments/").glob("*/manifest.yml")]


def list_copilot_local_services():
    return [path.parent.parts[-1] for path in Path("./copilot/").glob("*/manifest.yml")]


@click.group()
def copilot():
    pass


def _validate_and_normalise_config(config_file):
    """Load the storage.yaml file, validate it and return the normalised config
    dict."""

    def _lookup_plan(storage_type, env_conf):
        plan = env_conf.pop("plan", None)
        conf = storage_plans[storage_type][plan] if plan else {}
        conf.update(env_conf)

        return conf

    def _normalise_keys(source: dict):
        return {k.replace("-", "_"): v for k, v in source.items()}

    with open(PACKAGE_DIR / "storage-plans.yml", "r") as fd:
        storage_plans = yaml.safe_load(fd)

    with open(PACKAGE_DIR / "schemas/storage-schema.json", "r") as fd:
        schema = json.load(fd)

    # load and validate config
    with open(config_file, "r") as fd:
        config = yaml.safe_load(fd)

    # empty file
    if not config:
        return {}

    validate_json(instance=config, schema=schema)

    env_names = list_copilot_local_environments()
    svc_names = list_copilot_local_services()

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
            if type(normalised_config[storage_name]["services"]) == str:
                if normalised_config[storage_name]["services"] == "__all__":
                    normalised_config[storage_name]["services"] = svc_names
                else:
                    click.echo(
                        click.style(f"{storage_name}.services must be a list of service names or '__all__'", fg="red"),
                    )
                    exit(1)

            if not set(normalised_config[storage_name]["services"]).issubset(set(svc_names)):
                click.echo(
                    click.style(f"Services listed in {storage_name}.services do not exist in ./copilot/", fg="red"),
                )
                exit(1)

        environments = normalised_config[storage_name].pop("environments", {})
        default = environments.pop("default", {})

        initial = _lookup_plan(storage_type, default)

        if not set(environments.keys()).issubset(set(env_names)):
            click.echo(
                click.style(
                    f"Environment keys listed in {storage_name} do not match ./copilot/environments",
                    fg="red",
                ),
            )
            exit(1)

        normalised_environments = {}

        for env in env_names:
            normalised_environments[env] = _normalise_keys(initial)

        for env_name, env_config in environments.items():
            normalised_environments[env_name].update(_lookup_plan(storage_type, _normalise_keys(env_config)))

        normalised_config[storage_name]["environments"] = normalised_environments

    return normalised_config


@copilot.command()
def make_storage():
    """Generate storage CloudFormation for each environment."""

    overwrite = True
    output_dir = Path(".").absolute()

    ensure_cwd_is_repo_root()

    templates = setup_templates()

    config = _validate_and_normalise_config(PACKAGE_DIR / "default-storage.yml")

    project_config = _validate_and_normalise_config("storage.yml")

    config.update(project_config)

    click.echo("\n>>> Generating storage cloudformation\n")

    path = Path(f"copilot/environments/addons/")
    mkdir(output_dir, path)

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

        if storage_type not in ["s3", "s3-policy"]:
            contents = templates["env"]["parameters"].render({})

            click.echo(mkfile(output_dir, path / "addons.parameters.yml", contents, overwrite=overwrite))

        # s3-policy only applies to individual services
        if storage_type != "s3-policy":
            template = templates["env"][storage_type]
            contents = template.render({"service": service})

            click.echo(mkfile(output_dir, path / f"{storage_name}.yml", contents, overwrite=overwrite))

        # s3 buckets require additional service level cloudformation to grant the ECS task role access to the bucket
        if storage_type in ["s3", "s3-policy"]:
            template = templates["svc"]["s3-policy"]

            for svc in storage_config.get("services", []):
                service_path = Path(f"copilot/{svc}/addons/")

                service = {
                    "name": storage_config.get("name", None) or storage_name,
                    "prefix": camel_case(storage_name),
                    "environments": environments,
                    **storage_config,
                }

                contents = template.render({"service": service})

                mkdir(output_dir, service_path)
                click.echo(mkfile(output_dir, service_path / f"{storage_name}.yml", contents, overwrite=overwrite))

    click.echo(templates["storage-instructions"].render(services=services))


@copilot.command()
@click.argument("app", type=str)
@click.argument("env", type=str)
def get_env_secrets(app, env):
    """List secret names and values for an environment."""

    client = boto3.client("ssm")

    path = SSM_BASE_PATH.format(app=app, env=env)

    params = dict(Path=path, Recursive=False, WithDecryption=True, MaxResults=10)
    secrets = []

    # TODO: refactor shared code with get_ssm_secret_names
    while True:
        response = client.get_parameters_by_path(**params)

        for secret in response["Parameters"]:
            secrets.append(f"{secret['Name']:<8}: {secret['Value']:<15}")

        if "NextToken" in response:
            params["NextToken"] = response["NextToken"]
        else:
            break

    print("\n".join(sorted(secrets)))
