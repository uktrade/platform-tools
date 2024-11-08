#!/usr/bin/env python

import copy
import json
from pathlib import Path
from pathlib import PosixPath

import click
import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.utils.application import get_application_name
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.files import generate_override_files
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.template import camel_case
from dbt_platform_helper.utils.template import setup_templates
from dbt_platform_helper.utils.validation import config_file_check
from dbt_platform_helper.utils.validation import validate_addons
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)

PACKAGE_DIR = Path(__file__).resolve().parent.parent

WAF_ACL_ARN_KEY = "waf-acl-arn"

SERVICE_TYPES = [
    "Load Balanced Web Service",
    "Backend Service",
    "Request-Driven Web Service",
    "Static Site",
    "Worker Service",
]


def list_copilot_local_environments():
    return [
        path.parent.parts[-1] for path in Path("./copilot/environments/").glob("*/manifest.yml")
    ]


def is_service(path: PosixPath) -> bool:
    with open(path) as manifest_file:
        data = yaml.safe_load(manifest_file)
        if not data or not data.get("type"):
            click.echo(
                click.style(f"No type defined in manifest file {str(path)}; exiting", fg="red")
            )
            exit(1)

        return data.get("type") in SERVICE_TYPES


def list_copilot_local_services():
    return [
        path.parent.parts[-1]
        for path in Path("./copilot/").glob("*/manifest.yml")
        if is_service(path)
    ]


@click.group(chain=True, cls=ClickDocOptGroup)
def copilot():
    check_platform_helper_version_needs_update()


def _validate_and_normalise_extensions_config(config_file, key_in_config_file=None):
    """Load a config file, validate it against the extensions schemas and return
    the normalised config dict."""

    def _lookup_plan(addon_type, env_conf):
        plan = env_conf.pop("plan", None)
        conf = addon_plans[addon_type][plan] if plan else {}

        # Make a copy of the addon plan config so subsequent
        # calls do not override the root object
        conf = conf.copy()

        conf.update(env_conf)

        return conf

    def _normalise_keys(source: dict):
        return {k.replace("-", "_"): v for k, v in source.items()}

    with open(PACKAGE_DIR / "addon-plans.yml", "r") as fd:
        addon_plans = yaml.safe_load(fd)

    # load and validate config
    with open(config_file, "r") as fd:
        config = yaml.safe_load(fd)

    if config and key_in_config_file:
        config = config[key_in_config_file]

    # empty file
    if not config:
        return {}

    errors = validate_addons(config)

    if errors:
        click.echo(click.style(f"Errors found in {config_file}:", fg="red"))
        for addon, error in errors.items():
            click.echo(click.style(f"Addon '{addon}': {error}", fg="red"))
        exit(1)

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
    config_has_errors = False
    for addon_name, addon_config in config.items():
        addon_type = addon_config["type"]
        normalised_config[addon_name] = copy.deepcopy(addon_config)

        if "services" in normalised_config[addon_name]:
            if normalised_config[addon_name]["services"] == "__all__":
                normalised_config[addon_name]["services"] = svc_names

            if not set(normalised_config[addon_name]["services"]).issubset(set(svc_names)):
                click.echo(
                    click.style(
                        f"Services listed in {addon_name}.services do not exist in ./copilot/",
                        fg="red",
                    ),
                )
                config_has_errors = True

        environments = normalised_config[addon_name].pop("environments", {})
        default = environments.pop("*", environments.pop("default", {}))

        initial = _lookup_plan(addon_type, default)

        missing_envs = set(environments.keys()) - set(env_names)
        if missing_envs:
            click.echo(
                click.style(
                    f"Environment keys listed in {addon_name} do not match those defined in ./copilot/environments.",
                    fg="red",
                )
            ),
            click.echo(
                click.style(
                    f"  Missing environments: {', '.join(sorted(missing_envs))}",
                    fg="white",
                ),
            )
            config_has_errors = True

        if config_has_errors:
            continue

        normalised_environments = {}

        for env in env_names:
            normalised_environments[env] = _normalise_keys(initial)

        for env_name, env_config in environments.items():
            if env_config is None:
                env_config = {}
            normalised_environments[env_name].update(
                _lookup_plan(addon_type, _normalise_keys(env_config))
            )

        normalised_config[addon_name]["environments"] = normalised_environments

    if config_has_errors:
        exit(1)

    return normalised_config


def get_log_destination_arn():
    """Get destination arns stored in param store in projects aws account."""
    session = get_aws_session_or_abort()
    client = session.client("ssm", region_name="eu-west-2")
    response = client.get_parameters(Names=["/copilot/tools/central_log_groups"])

    if not response["Parameters"]:
        click.echo(
            click.style(
                "No aws central log group defined in Parameter Store at location /copilot/tools/central_log_groups; exiting",
                fg="red",
            )
        )
        exit(1)

    destination_arns = json.loads(response["Parameters"][0]["Value"])
    return destination_arns


def _generate_svc_overrides(base_path, templates, name):
    click.echo(f"\n>>> Generating service overrides for {name}\n")
    overrides_path = base_path.joinpath(f"copilot/{name}/overrides")
    overrides_path.mkdir(parents=True, exist_ok=True)
    overrides_file = overrides_path.joinpath("cfn.patches.yml")
    overrides_file.write_text(templates.get_template("svc/overrides/cfn.patches.yml").render())


def _get_s3_kms_alias_arns(session, application_name, config):
    application = load_application(application_name, session)
    arns = {}

    for environment_name in application.environments:
        if environment_name not in config:
            continue

        if "bucket_name" not in config[environment_name]:
            continue

        bucket_name = config[environment_name]["bucket_name"]
        kms_client = application.environments[environment_name].session.client("kms")
        alias_name = f"alias/{application_name}-{environment_name}-{bucket_name}-key"

        try:
            response = kms_client.describe_key(KeyId=alias_name)
        except kms_client.exceptions.NotFoundException:
            pass
        else:
            arns[environment_name] = response["KeyMetadata"]["Arn"]

    return arns


@copilot.command()
def make_addons():
    """Generate addons CloudFormation for each environment."""
    output_dir = Path(".").absolute()
    config_file_check()

    templates = setup_templates()
    config = _get_config()
    session = get_aws_session_or_abort()

    application_name = get_application_name()

    with open(PACKAGE_DIR / "addons-template-map.yml") as fd:
        addon_template_map = yaml.safe_load(fd)

    click.echo("\n>>> Generating Terraform compatible addons CloudFormation\n")

    env_path = Path(f"copilot/environments/")
    env_addons_path = env_path / "addons"
    env_overrides_path = env_path / "overrides"

    _cleanup_old_files(config, output_dir, env_addons_path, env_overrides_path)
    _generate_env_overrides(output_dir)

    svc_names = list_copilot_local_services()
    base_path = Path(".")
    for svc_name in svc_names:
        _generate_svc_overrides(base_path, templates, svc_name)

    services = []
    for addon_name, addon_config in config.items():
        print(f">>>>>>>>> {addon_name}")
        addon_type = addon_config.pop("type")
        environments = addon_config.pop("environments")
        if addon_template_map[addon_type].get("requires_addons_parameters", False):
            pass
        if addon_type in ["postgres"]:
            pass

        environment_addon_config = {
            "addon_type": addon_type,
            "environments": environments,
            "name": addon_config.get("name", None) or addon_name,
            "prefix": camel_case(addon_name),
            "secret_name": addon_name.upper().replace("-", "_"),
            **addon_config,
        }

        services.append(environment_addon_config)

        service_addon_config = {
            "application_name": application_name,
            "name": addon_config.get("name", None) or addon_name,
            "prefix": camel_case(addon_name),
            "environments": environments,
            **addon_config,
        }

        log_destination_arns = get_log_destination_arn()

        if addon_type in ["s3", "s3-policy"]:
            if config[addon_name].get("serve_static_content"):
                continue

            s3_kms_arns = _get_s3_kms_alias_arns(session, application_name, environments)
            for environment_name in environments:
                environments[environment_name]["kms_key_arn"] = s3_kms_arns.get(
                    environment_name, "kms-key-not-found"
                )

        _generate_service_addons(
            addon_config,
            addon_name,
            addon_template_map,
            addon_type,
            output_dir,
            service_addon_config,
            templates,
            log_destination_arns,
        )

    click.echo(templates.get_template("addon-instructions.txt").render(services=services))


def _get_config():
    config = _validate_and_normalise_extensions_config(PACKAGE_DIR / "default-extensions.yml")
    project_config = _validate_and_normalise_extensions_config(PLATFORM_CONFIG_FILE, "extensions")
    config.update(project_config)
    return config


def _generate_env_overrides(output_dir):
    path = "templates/env/terraform-overrides"
    click.echo("\n>>> Generating Environment overrides\n")
    overrides_path = output_dir.joinpath(f"copilot/environments/overrides")
    overrides_path.mkdir(parents=True, exist_ok=True)
    template_overrides_path = Path(__file__).parent.parent.joinpath(path)
    generate_override_files(Path("."), template_overrides_path, overrides_path)


def _generate_service_addons(
    addon_config,
    addon_name,
    addon_template_map,
    addon_type,
    output_dir,
    service_addon_config,
    templates,
    log_destination_arns,
):
    # generate svc addons
    for addon in addon_template_map[addon_type].get("svc", []):
        template = templates.get_template(addon["template"])

        for svc in addon_config.get("services", []):
            service_path = Path(f"copilot/{svc}/addons/")

            contents = template.render(
                {
                    "addon_config": service_addon_config,
                    "log_destination": log_destination_arns,
                }
            )

            filename = addon.get("filename", f"{addon_name}.yml")

            (output_dir / service_path).mkdir(parents=True, exist_ok=True)
            click.echo(mkfile(output_dir, service_path / filename, contents, overwrite=True))


def _cleanup_old_files(config, output_dir, env_addons_path, env_overrides_path):
    def _rmdir(path):
        if not path.exists():
            return
        for f in path.iterdir():
            if f.is_file():
                f.unlink()
            if f.is_dir():
                _rmdir(f)
                f.rmdir()

    _rmdir(output_dir / env_addons_path)
    _rmdir(output_dir / env_overrides_path)

    all_services = set()
    for services in [v["services"] for v in config.values() if "services" in v]:
        all_services.update(services)

    for service in all_services:
        svc_addons_dir = Path(output_dir, "copilot", service, "addons")
        if not svc_addons_dir.exists():
            continue
        for f in svc_addons_dir.iterdir():
            if f.is_file():
                f.unlink()
