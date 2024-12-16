import os
import re
from pathlib import Path

import click
import yaml
from schema import SchemaError
from yaml.parser import ParserError

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.platform_config_schema import PlatformConfigSchema
from dbt_platform_helper.utils.aws import get_supported_opensearch_versions
from dbt_platform_helper.utils.aws import get_supported_redis_versions
from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.messages import abort_with_error


def validate_addons(addons: dict):
    """
    Validate the addons file and return a dictionary of addon: error message.
    """
    errors = {}

    for addon_name, addon in addons.items():
        try:
            addon_type = addon.get("type", None)
            if not addon_type:
                errors[addon_name] = f"Missing addon type in addon '{addon_name}'"
                continue
            schema = PlatformConfigSchema.extension_schemas().get(addon_type, None)
            if not schema:
                errors[addon_name] = (
                    f"Unsupported addon type '{addon_type}' in addon '{addon_name}'"
                )
                continue
            schema.validate(addon)
        except SchemaError as ex:
            errors[addon_name] = f"Error in {addon_name}: {ex.code}"

    ConfigProvider.validate_extension_supported_versions(
        config={"extensions": addons},
        extension_type="redis",
        version_key="engine",
        get_supported_versions=get_supported_redis_versions,
    )
    ConfigProvider.validate_extension_supported_versions(
        config={"extensions": addons},
        extension_type="opensearch",
        version_key="engine",
        get_supported_versions=get_supported_opensearch_versions,
    )

    return errors


def float_between_with_halfstep(lower, upper):
    def is_between(value):
        is_number = isinstance(value, int) or isinstance(value, float)
        is_half_step = re.match(r"^\d+(\.[05])?$", str(value))

        if is_number and is_half_step and lower <= value <= upper:
            return True
        raise SchemaError(f"should be a number between {lower} and {upper} in increments of 0.5")

    return is_between


def validate_platform_config(config):
    PlatformConfigSchema.schema().validate(config)
    enriched_config = apply_environment_defaults(config)
    ConfigProvider.validate_environment_pipelines(enriched_config)
    ConfigProvider.validate_environment_pipelines_triggers(enriched_config)
    ConfigProvider.validate_codebase_pipelines(enriched_config)
    validate_database_copy_section(enriched_config)

    ConfigProvider.validate_extension_supported_versions(
        config=config,
        extension_type="redis",
        version_key="engine",
        get_supported_versions=get_supported_redis_versions,
    )
    ConfigProvider.validate_extension_supported_versions(
        config=config,
        extension_type="opensearch",
        version_key="engine",
        get_supported_versions=get_supported_opensearch_versions,
    )


def validate_database_copy_section(config):
    extensions = config.get("extensions", {})
    if not extensions:
        return

    postgres_extensions = {
        key: ext for key, ext in extensions.items() if ext.get("type", None) == "postgres"
    }

    if not postgres_extensions:
        return

    errors = []

    for extension_name, extension in postgres_extensions.items():
        database_copy_sections = extension.get("database_copy", [])

        if not database_copy_sections:
            return

        all_environments = [env for env in config.get("environments", {}).keys() if not env == "*"]
        all_envs_string = ", ".join(all_environments)

        for section in database_copy_sections:
            from_env = section["from"]
            to_env = section["to"]

            from_account = ConfigProvider.get_env_deploy_account_info(config, from_env, "id")
            to_account = ConfigProvider.get_env_deploy_account_info(config, to_env, "id")

            if from_env == to_env:
                errors.append(
                    f"database_copy 'to' and 'from' cannot be the same environment in extension '{extension_name}'."
                )

            if "prod" in to_env:
                errors.append(
                    f"Copying to a prod environment is not supported: database_copy 'to' cannot be '{to_env}' in extension '{extension_name}'."
                )

            if from_env not in all_environments:
                errors.append(
                    f"database_copy 'from' parameter must be a valid environment ({all_envs_string}) but was '{from_env}' in extension '{extension_name}'."
                )

            if to_env not in all_environments:
                errors.append(
                    f"database_copy 'to' parameter must be a valid environment ({all_envs_string}) but was '{to_env}' in extension '{extension_name}'."
                )

            if from_account != to_account:
                if "from_account" not in section:
                    errors.append(
                        f"Environments '{from_env}' and '{to_env}' are in different AWS accounts. The 'from_account' parameter must be present."
                    )
                elif section["from_account"] != from_account:
                    errors.append(
                        f"Incorrect value for 'from_account' for environment '{from_env}'"
                    )

                if "to_account" not in section:
                    errors.append(
                        f"Environments '{from_env}' and '{to_env}' are in different AWS accounts. The 'to_account' parameter must be present."
                    )
                elif section["to_account"] != to_account:
                    errors.append(f"Incorrect value for 'to_account' for environment '{to_env}'")

    if errors:
        abort_with_error("\n".join(errors))


def load_and_validate_platform_config(path=PLATFORM_CONFIG_FILE, disable_file_check=False):
    if not disable_file_check:
        config_file_check(path)
    try:
        conf = yaml.safe_load(Path(path).read_text())
        config_provider = ConfigProvider()

        duplicate_keys = config_provider.lint_yaml_for_duplicate_keys(path)
        if duplicate_keys:
            abort_with_error(
                "Duplicate keys found in platform-config:"
                + os.linesep
                + os.linesep.join(duplicate_keys)
            )
        validate_platform_config(conf)
        return conf
    except ParserError:
        abort_with_error(f"{PLATFORM_CONFIG_FILE} is not valid YAML")
    except SchemaError as e:
        abort_with_error(f"Schema error in {PLATFORM_CONFIG_FILE}. {e}")


def config_file_check(path=PLATFORM_CONFIG_FILE):
    platform_config_exists = Path(path).exists()
    errors = []
    warnings = []

    messages = {
        "storage.yml": {"instruction": " under the key 'extensions'", "type": errors},
        "extensions.yml": {"instruction": " under the key 'extensions'", "type": errors},
        "pipelines.yml": {
            "instruction": ", change the key 'codebases' to 'codebase_pipelines'",
            "type": errors,
        },
        PLATFORM_HELPER_VERSION_FILE: {
            "instruction": ", under the key `default_versions: platform-helper:`",
            "type": warnings,
        },
    }

    for file in messages.keys():
        if Path(file).exists():
            message = (
                f"`{file}` is no longer supported. Please move its contents into the "
                f"`{PLATFORM_CONFIG_FILE}` file{messages[file]['instruction']} and delete `{file}`."
            )
            messages[file]["type"].append(message)

    if not errors and not warnings and not platform_config_exists:
        errors.append(
            f"`{PLATFORM_CONFIG_FILE}` is missing. "
            "Please check it exists and you are in the root directory of your deployment project."
        )

    if warnings:
        click.secho("\n".join(warnings), bg="yellow", fg="black")
    if errors:
        click.secho("\n".join(errors), bg="red", fg="white")
        exit(1)
