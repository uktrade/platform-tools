from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
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
        platform_helper_version_status: PlatformHelperVersionStatus = PlatformHelperVersionStatus(),
        platform_helper_versioning: PlatformHelperVersioning = PlatformHelperVersioning(),
    ):
        self.io = io
        self.config_provider = config_provider
        self.manifest_provider = manifest_provider or TerraformManifestProvider()
        self.platform_helper_version_status = platform_helper_version_status
        self.platform_helper_versioning = platform_helper_versioning

    def generate(
        self,
        environment_name: str,
        cli_platform_helper_version: str = None,
    ):
        config = self.config_provider.get_enriched_config()

        if environment_name not in config.get("environments").keys():
            raise EnvironmentNotFoundException(
                f"cannot generate terraform for environment {environment_name}.  It does not exist in your configuration"
            )

        # platform_config_platform_helper_default_version = config.get("default_versions", {}).get(
        #     "platform-helper"
        # )

        # self.platform_helper_version_status.cli_override = cli_platform_helper_version
        # self.platform_helper_version_status.platform_config_default = (
        #     platform_config_platform_helper_default_version
        # )

        # platform_helper_version = (
        #     self.platform_helper_version_status.get_required_platform_helper_version(self.io)
        # )

        platform_helper_version = (
            self.platform_helper_versioning.get_required_platform_helper_version(
                self.io, cli_platform_helper_version
            )
        )

        self.manifest_provider.generate_environment_config(
            config, environment_name, platform_helper_version
        )
