from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION


class TerraformPlatformModulesVersioning:
    def __init__(self):
        pass

    def get_required_version(
        self,
        version_override: str,
        platform_config_default_version: str,
    ) -> str:
        version_preference_order = [
            version_override,
            platform_config_default_version,
            DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION,
        ]
        return [version for version in version_preference_order if version][0]
