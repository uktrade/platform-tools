from schema import SchemaError

from dbt_platform_helper.entities.platform_config_schema import PlatformConfigSchema
from dbt_platform_helper.providers.config_validator import ConfigValidator


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

    ConfigValidator().validate_supported_redis_versions({"extensions": addons})
    ConfigValidator().validate_supported_opensearch_versions({"extensions": addons})

    return errors
