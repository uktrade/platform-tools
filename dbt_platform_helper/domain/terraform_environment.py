from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_OVERRIDE_KEY
from dbt_platform_helper.constants import (
    TERRAFORM_EXTENSIONS_MODULE_SOURCE_OVERRIDE_ENV_VAR,
)
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.environment_variable import (
    EnvironmentVariableProvider,
)
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider


class TerraformEnvironmentException(PlatformException):
    pass


class EnvironmentNotFoundException(TerraformEnvironmentException):
    pass


class TerraformEnvironment:
    def __init__(
        self,
        config_provider,
        manifest_provider: TerraformManifestProvider = None,
        environment_variable_provider: EnvironmentVariableProvider = None,
        io: ClickIOProvider = ClickIOProvider(),
        platform_helper_version_override: str = None,
    ):
        self.io = io
        self.config_provider = config_provider
        self.manifest_provider = manifest_provider or TerraformManifestProvider()
        self.environment_variable_provider = (
            environment_variable_provider or EnvironmentVariableProvider()
        )
        self.platform_helper_version_override = (
            platform_helper_version_override
            or self.environment_variable_provider.get(PLATFORM_HELPER_VERSION_OVERRIDE_KEY)
        )

    def generate(
        self,
        environment_name: str,
    ):

        config = self.config_provider.get_enriched_config()

        if environment_name not in config.get("environments").keys():
            raise EnvironmentNotFoundException(
                f"cannot generate terraform for environment {environment_name}.  It does not exist in your configuration"
            )

        platform_helper_version_for_template: str = config.get("default_versions", {}).get(
            "platform-helper"
        )

        if self.platform_helper_version_override:
            platform_helper_version_for_template = self.platform_helper_version_override

        module_source_override = self.environment_variable_provider.get(
            TERRAFORM_EXTENSIONS_MODULE_SOURCE_OVERRIDE_ENV_VAR
        )

        self.manifest_provider.generate_environment_config(
            config,
            environment_name,
            platform_helper_version_for_template,
            module_source_override,
        )
