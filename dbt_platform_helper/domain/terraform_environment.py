import click

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.constants import SUPPORTED_AWS_PROVIDER_VERSION
from dbt_platform_helper.constants import SUPPORTED_TERRAFORM_VERSION
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.utils.template import setup_templates


class PlatformTerraformManifestGenerator:
    def __init__(self, file_provider):
        self.file_provider = file_provider
        self.manifest_template = setup_templates().get_template("environments/main.tf")

    def generate_manifest(
        self,
        environment_name: str,
        application_name: str,
        environment_config: dict,
        terraform_platform_modules_version_override: str = None,
    ):
        terraform_platform_modules_version = (
            terraform_platform_modules_version_override
            or environment_config.get("versions", {}).get(
                "terraform-platform-modules", DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
            )
        )

        return self.manifest_template.render(
            {
                "application": application_name,
                "environment": environment_name,
                "config": environment_config,
                "terraform_platform_modules_version": terraform_platform_modules_version,
                "terraform_version": SUPPORTED_TERRAFORM_VERSION,
                "aws_provider_version": SUPPORTED_AWS_PROVIDER_VERSION,
            }
        )

    def write_manifest(self, environment_name: str, manifest_content: str):
        return self.file_provider.mkfile(
            ".",
            f"terraform/environments/{environment_name}/main.tf",
            manifest_content,
            overwrite=True,
        )


class TerraformEnvironmentException(PlatformException):
    pass


class EnvironmentNotFoundException(TerraformEnvironmentException):
    pass


class TerraformEnvironment:
    def __init__(
        self,
        config_provider,
        manifest_generator: PlatformTerraformManifestGenerator = None,
        echo=click.echo,
    ):
        self.echo = echo
        self.config_provider = config_provider
        self.manifest_generator = manifest_generator or PlatformTerraformManifestGenerator(
            FileProvider()
        )

    def generate(self, environment_name, terraform_platform_modules_version_override=None):
        config = self.config_provider.get_enriched_config()

        if environment_name not in config.get("environments").keys():
            raise EnvironmentNotFoundException(
                f"cannot generate terraform for environment {environment_name}.  It does not exist in your configuration"
            )

        manifest = self.manifest_generator.generate_manifest(
            environment_name=environment_name,
            application_name=config["application"],
            environment_config=config["environments"][environment_name],
            terraform_platform_modules_version_override=terraform_platform_modules_version_override,
        )

        self.echo(
            self.manifest_generator.write_manifest(
                environment_name=environment_name, manifest_content=manifest
            )
        )
