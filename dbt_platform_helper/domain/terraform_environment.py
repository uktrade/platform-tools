import click

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.utils.template import setup_templates


class PlatformTerraformManifestGenerator:
    def __init__(self):
        self.manifest_template = setup_templates().get_template("environments/main.tf")

    def generate_manifest(
        self,
        application_name: str,
        environment_name: str,
        environment_config,
        terraform_platform_modules_version_override=None,
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

    def write_manifest():
        pass


class TerraformEnvironment:
    def __init__(self, config_provider, echo_fn=click.echo):
        self.echo = echo_fn
        self.config_provider = config_provider
        self.template = setup_templates().get_template("environments/main.tf")
        self.config = self.config_provider.apply_environment_defaults(
            self.config_provider.load_and_validate_platform_config()
        )

    def generate(self, environment_name, terraform_platform_modules_version_override=None):
        terraform_platform_modules_version = (
            terraform_platform_modules_version_override
            or self.config["environments"][environment_name]
            .get("versions", {})
            .get("terraform-platform-modules")
            or DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
        )

        contents = self.template.render(
            {
                "application": self.config["application"],
                "environment": environment_name,
                "config": self.config["environments"][environment_name],
                "terraform_platform_modules_version": terraform_platform_modules_version,
            }
        )

        self.echo(
            FileProvider.mkfile(
                ".", f"terraform/environments/{environment_name}/main.tf", contents, overwrite=True
            )
        )
