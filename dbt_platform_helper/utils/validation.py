import boto3
from schema import SchemaError

from dbt_platform_helper.providers.config import PlatformConfigValidator
from dbt_platform_helper.providers.opensearch import OpensearchProvider
from dbt_platform_helper.providers.platform_config_schema import PlatformConfigSchema
from dbt_platform_helper.providers.redis import RedisProvider


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
