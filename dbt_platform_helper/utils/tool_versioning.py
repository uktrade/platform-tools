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
