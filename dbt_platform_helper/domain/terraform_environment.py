from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.legacy_versions import LegacyVersionsProvider
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider
from dbt_platform_helper.providers.version_status import PlatformHelperVersionStatus


class TerraformEnvironmentException(PlatformException):
    pass


class EnvironmentNotFoundException(TerraformEnvironmentException):
    pass


class TerraformEnvironment:
    def __init__(
        self,
        config_provider,
        manifest_provider: TerraformManifestProvider = None,
        io: ClickIOProvider = ClickIOProvider(),
        legacy_versions_provider: LegacyVersionsProvider = LegacyVersionsProvider(),
    ):
        self.io = io
        self.config_provider = config_provider
        self.manifest_provider = manifest_provider or TerraformManifestProvider()
        self.legacy_versions_provider = legacy_versions_provider

    def generate(
        self,
        environment_name,
        cli_platform_helper_version=None,
        cli_terraform_platform_modules_version=None,
    ):
        config = self.config_provider.get_enriched_config()

        self.legacy_versions_provider.check_terraform_platform_modules_version(
            cli_terraform_platform_modules_version, config
        )

        if environment_name not in config.get("environments").keys():
            raise EnvironmentNotFoundException(
                f"cannot generate terraform for environment {environment_name}.  It does not exist in your configuration"
            )

        platform_config_platform_helper_default_version = config.get("default_versions", {}).get(
            "platform-helper"
        )

        platform_helper_version = PlatformHelperVersionStatus(
            cli_override=cli_platform_helper_version,
            platform_config_default=platform_config_platform_helper_default_version,
        ).get_required_platform_helper_version(self.io)

        self.manifest_provider.generate_environment_config(
            config, environment_name, platform_helper_version
        )
