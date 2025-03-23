from dbt_platform_helper.constants import DEFAULT_PLATFORM_HELPER_VERSION


def get_required_platform_helper_version(
    cli_platform_helper_version, platform_config_platform_helper_default_version
):
    version_preference_order = [
        cli_platform_helper_version,
        platform_config_platform_helper_default_version,
        DEFAULT_PLATFORM_HELPER_VERSION,
    ]
    return [version for version in version_preference_order if version][0]
