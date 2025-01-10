import click

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.utils.template import setup_templates


class PlatformTerraformManifestGenerator:
    def __init__(self, file_provider):
        self.file_provider = file_provider
        self.manifest_template = setup_templates().get_template("environments/main.tf")

    def generate_manifest(
        self,
        application_name: str,
        environment_name: str,
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
            }
        )

    def write_manifest(self, environment_name: str, manifest_content: str):
        return self.file_provider.mkfile(
            ".",
            f"terraform/environments/{environment_name}/main.tf",
            manifest_content,
            overwrite=True,
        )


class TerraformEnvironment:
    def __init__(self, config_provider, echo_fn=click.echo):
        self.echo = echo_fn
        self.config_provider = config_provider

    def generate(self, environment_name, terraform_platform_modules_version_override=None):
        config = self.config_provider.apply_environment_defaults(
            self.config_provider.load_and_validate_platform_config()
        )

        manifest_generator = PlatformTerraformManifestGenerator(FileProvider())

        manifest = manifest_generator.generate_manifest(
            environment_name,
            config["application"],
            config["environments"][environment_name],
            terraform_platform_modules_version_override,
        )

        self.echo(manifest_generator.write_manifest(environment_name, manifest))
