from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.providers.io import ClickIOProvider


def get_required_platform_helper_version(
    cli_platform_helper_version, platform_config_platform_helper_default_version
):

    platform_helper_versioning = PlatformHelperVersioning(io=ClickIOProvider())

    required_version = platform_helper_versioning.get_required_version(pipeline=None)

    version_preference_order = [
        cli_platform_helper_version,
        platform_config_platform_helper_default_version,
        required_version,
    ]
    return [version for version in version_preference_order if version][0]


def check_terraform_platform_modules_version(self, cli_terraform_platform_modules_version, config):
    has_deprecated_default = config.get("default_versions", {}).get("terraform-platform-modules")

    has_deprecated_version = any(
        "versions" in env and "terraform-platform-modules" in env["versions"]
        for env in config.get("environments", {}).values()
        if isinstance(env, dict)
    )

    if cli_terraform_platform_modules_version or has_deprecated_default or has_deprecated_version:
        self.io.warn(
            "The `--terraform-platform-modules-version` flag for the pipeline generate command is deprecated. "
            "Please use the `--platform-helper-version` flag instead.\n\n"
            "The `terraform-platform-modules` key set in `default_versions: terraform-platform-modules` and "
            "`environments: <env>: versions: terraform-platform-modules`, are deprecated. "
            "Please use the `default_versions: platform-helper` value instead. "
            "See full platform config reference in the docs: "
            "https://platform.readme.trade.gov.uk/reference/platform-config-yml/#core-configuration"
        )
