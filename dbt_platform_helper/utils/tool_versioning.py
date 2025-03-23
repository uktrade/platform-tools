from dbt_platform_helper.constants import DEFAULT_PLATFORM_HELPER_VERSION
from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION

def get_required_terraform_platform_modules_version(
    cli_terraform_platform_modules_version, platform_config_terraform_modules_default_version
):
    version_preference_order = [
        cli_terraform_platform_modules_version,
        platform_config_terraform_modules_default_version,
        DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION,
    ]
    return [version for version in version_preference_order if version][0]


def get_required_platform_helper_version(
    cli_platform_helper_version, platform_config_platform_helper_default_version
):
    version_preference_order = [
        cli_platform_helper_version,
        platform_config_platform_helper_default_version,
        DEFAULT_PLATFORM_HELPER_VERSION,
    ]
    return [version for version in version_preference_order if version][0]
