#!/usr/bin/env python

import copy
import json
from pathlib import Path

import boto3
import click
import yaml
from jsonschema import validate as validate_json

from dbt_copilot_helper.utils import SSM_BASE_PATH
from dbt_copilot_helper.utils import ClickDocOptGroup
from dbt_copilot_helper.utils import camel_case
from dbt_copilot_helper.utils import ensure_cwd_is_repo_root
from dbt_copilot_helper.utils import mkdir
from dbt_copilot_helper.utils import mkfile
from dbt_copilot_helper.utils import setup_templates

PACKAGE_DIR = Path(__file__).resolve().parent.parent

WAF_ACL_ARN_KEY = "waf-acl-arn"


def list_copilot_local_environments():
    return [
        path.parent.parts[-1] for path in Path("./copilot/environments/").glob("*/manifest.yml")
    ]


def list_copilot_local_services():
    return [path.parent.parts[-1] for path in Path("./copilot/").glob("*/manifest.yml")]


@click.group(cls=ClickDocOptGroup)
def copilot():
    pass


def _validate_and_normalise_config(config_file):
    """Load the addons.yaml file, validate it and return the normalised config
    dict."""

    def _lookup_plan(addon_type, env_conf):
        plan = env_conf.pop("plan", None)
        conf = addon_plans[addon_type][plan] if plan else {}
        conf.update(env_conf)

        return conf

    def _normalise_keys(source: dict):
        return {k.replace("-", "_"): v for k, v in source.items()}

    with open(PACKAGE_DIR / "addon-plans.yml", "r") as fd:
        addon_plans = yaml.safe_load(fd)

    with open(PACKAGE_DIR / "schemas/addons-schema.json", "r") as fd:
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
        click.echo(
            click.style(f"No environments found in ./copilot/environments; exiting", fg="red")
        )
        exit(1)

    if not svc_names:
        click.echo(click.style(f"No services found in ./copilot/; exiting", fg="red"))
        exit(1)

    normalised_config = {}
    for addon_name, addon_config in config.items():
        addon_type = addon_config["type"]
        normalised_config[addon_name] = copy.deepcopy(addon_config)

        if "services" in normalised_config[addon_name]:
            if type(normalised_config[addon_name]["services"]) == str:
                if normalised_config[addon_name]["services"] == "__all__":
                    normalised_config[addon_name]["services"] = svc_names
                else:
                    click.echo(
                        click.style(
                            f"{addon_name}.services must be a list of service names or '__all__'",
                            fg="red",
                        ),
                    )
                    exit(1)

            if not set(normalised_config[addon_name]["services"]).issubset(set(svc_names)):
                click.echo(
                    click.style(
                        f"Services listed in {addon_name}.services do not exist in ./copilot/",
                        fg="red",
                    ),
                )
                exit(1)

        environments = normalised_config[addon_name].pop("environments", {})
        default = environments.pop("default", {})

        initial = _lookup_plan(addon_type, default)

        if not set(environments.keys()).issubset(set(env_names)):
            click.echo(
                click.style(
                    f"Environment keys listed in {addon_name} do not match ./copilot/environments",
                    fg="red",
                ),
            )
            exit(1)

        normalised_environments = {}

        for env in env_names:
            normalised_environments[env] = _normalise_keys(initial)

        for env_name, env_config in environments.items():
            normalised_environments[env_name].update(
                _lookup_plan(addon_type, _normalise_keys(env_config))
            )

        normalised_config[addon_name]["environments"] = normalised_environments

    return normalised_config


@copilot.command()
def make_addons():
    """Generate addons CloudFormation for each environment."""

    overwrite = True
    output_dir = Path(".").absolute()

    ensure_cwd_is_repo_root()

    templates = setup_templates()

    config = _validate_and_normalise_config(PACKAGE_DIR / "default-addons.yml")
    project_config = _validate_and_normalise_config("addons.yml")
    config.update(project_config)

    with open(PACKAGE_DIR / "addons-template-map.yml") as fd:
        addon_template_map = yaml.safe_load(fd)

    click.echo("\n>>> Generating addons CloudFormation\n")

    path = Path(f"copilot/environments/addons/")
    mkdir(output_dir, path)

    services = []
    for addon_name, addon_config in config.items():
        print(f">>>>>>>>> {addon_name}")
        addon_type = addon_config.pop("type")
        environments = addon_config.pop("environments")

        environment_addon_config = {
            "secret_name": addon_name.upper().replace("-", "_"),
            "name": addon_config.get("name", None) or addon_name,
            "environments": environments,
            "prefix": camel_case(addon_name),
            "addon_type": addon_type,
            **addon_config,
        }

        services.append(environment_addon_config)

        service_addon_config = {
            "name": addon_config.get("name", None) or addon_name,
            "prefix": camel_case(addon_name),
            "environments": environments,
            **addon_config,
        }

        # generate env addons
        for addon in addon_template_map[addon_type].get("env", []):
            template = templates.get_template(addon["template"])

            contents = template.render({"service": environment_addon_config})

            filename = addon.get("filename", f"{addon_name}.yml")

            click.echo(mkfile(output_dir, path / filename, contents, overwrite=overwrite))

        # generate svc addons
        for addon in addon_template_map[addon_type].get("svc", []):
            template = templates.get_template(addon["template"])

            for svc in addon_config.get("services", []):
                service_path = Path(f"copilot/{svc}/addons/")

                contents = template.render({"service": service_addon_config})

                filename = addon.get("filename", f"{addon_name}.yml")

                mkdir(output_dir, service_path)
                click.echo(
                    mkfile(output_dir, service_path / filename, contents, overwrite=overwrite)
                )

        if addon_type in ["aurora-postgres", "rds-postgres"]:
            click.secho(
                "\nNote: The key DATABASE_CREDENTIALS may need to be changed to match your Django settings configuration.",
                fg="yellow",
            )

    click.echo(templates.get_template("addon-instructions.txt").render(services=services))


@copilot.command()
@click.argument("app", type=str, required=True)
@click.argument("env", type=str, required=True)
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
