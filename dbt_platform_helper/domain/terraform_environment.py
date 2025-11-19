from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
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
        io: ClickIOProvider = ClickIOProvider(),
        platform_helper_versioning: PlatformHelperVersioning = None,
    ):
        self.io = io
        self.config_provider = config_provider
        self.manifest_provider = manifest_provider or TerraformManifestProvider()
        self.platform_helper_versioning = platform_helper_versioning

    def generate(
        self,
        environment_name: str,
    ):

        config = self.config_provider.get_enriched_config()

        if environment_name not in config.get("environments").keys():
            raise EnvironmentNotFoundException(
                f"cannot generate terraform for environment {environment_name}.  It does not exist in your configuration"
            )

        self.manifest_provider.generate_environment_config(
            config,
            environment_name,
            self.platform_helper_versioning.get_template_version(),
            self.platform_helper_versioning.get_extensions_module_version(),
        )
