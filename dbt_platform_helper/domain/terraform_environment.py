from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider
from dbt_platform_helper.utils.tool_versioning import (
    get_required_terraform_platform_modules_version,
)


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
    ):
        self.io = io
        self.config_provider = config_provider
        self.manifest_provider = manifest_provider or TerraformManifestProvider()

    def generate(self, environment_name, terraform_platform_modules_version_override=None):
        config = self.config_provider.get_enriched_config()

        if environment_name not in config.get("environments").keys():
            raise EnvironmentNotFoundException(
                f"cannot generate terraform for environment {environment_name}.  It does not exist in your configuration"
            )

        platform_config_terraform_modules_default_version = config.get("default_versions", {}).get(
            "terraform-platform-modules", ""
        )
        terraform_platform_modules_version = get_required_terraform_platform_modules_version(
            terraform_platform_modules_version_override,
            platform_config_terraform_modules_default_version,
        )

        self.manifest_provider.generate_environment_config(
            config, environment_name, terraform_platform_modules_version
        )
