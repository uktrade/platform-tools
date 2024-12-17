import os
from pathlib import Path

import boto3
import click
import yaml
from schema import SchemaError
from yaml.parser import ParserError

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config import PlatformConfigValidator
from dbt_platform_helper.providers.opensearch import OpensearchProvider
from dbt_platform_helper.providers.platform_config_schema import PlatformConfigSchema
from dbt_platform_helper.providers.redis import RedisProvider
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

    PlatformConfigValidator.validate_extension_supported_versions(
        config={"extensions": addons},
        extension_type="redis",
        version_key="engine",
        get_supported_versions=RedisProvider(
            boto3.client("elasticache")
        ).get_supported_redis_versions,
    )
    PlatformConfigValidator.validate_extension_supported_versions(
        config={"extensions": addons},
        extension_type="opensearch",
        version_key="engine",
        get_supported_versions=OpensearchProvider(
            boto3.client("opensearch")
        ).get_supported_opensearch_versions,
    )

    return errors


def validate_platform_config(config):
    PlatformConfigSchema.schema().validate(config)

    # TODO= logically this isn't validation but loading + parsing, to move.
    enriched_config = apply_environment_defaults(config)
    PlatformConfigValidator.validate_environment_pipelines(enriched_config)
    PlatformConfigValidator.validate_environment_pipelines_triggers(enriched_config)
    PlatformConfigValidator.validate_codebase_pipelines(enriched_config)
    PlatformConfigValidator.validate_database_copy_section(enriched_config)

    PlatformConfigValidator.validate_extension_supported_versions(
        config=config,
        extension_type="redis",
        version_key="engine",
        get_supported_versions=RedisProvider(
            boto3.client("elasticache")
        ).get_supported_redis_versions,
    )
    PlatformConfigValidator.validate_extension_supported_versions(
        config=config,
        extension_type="opensearch",
        version_key="engine",
        get_supported_versions=OpensearchProvider(
            boto3.client("opensearch")
        ).get_supported_opensearch_versions,
    )


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

    if not platform_config_exists:
        click.secho(
            f"`{PLATFORM_CONFIG_FILE}` is missing. "
            "Please check it exists and you are in the root directory of your deployment project."
        )
        exit(1)
