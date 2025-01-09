import click

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.utils.template import setup_templates


class TerraformEnvironment:
    def __init__(self, config_provider):
        self.config_provider = config_provider
        self.template = setup_templates().get_template("environments/main.tf")
        self.config = self.config_provider.apply_environment_defaults(
            self.config_provider.load_and_validate_platform_config()
        )

    def generate(self, environment_name, terraform_platform_modules_version_override=None):
        env_config = self.config["environments"][environment_name]

        contents = self.template.render(
            {
                "application": self.config["application"],
                "environment": environment_name,
                "config": env_config,
                "terraform_platform_modules_version": self._determine_terraform_platform_modules_version(
                    env_config, terraform_platform_modules_version_override
                ),
            }
        )

        click.echo(
            FileProvider.mkfile(
                ".", f"terraform/environments/{environment_name}/main.tf", contents, overwrite=True
            )
        )

    def _determine_terraform_platform_modules_version(
        self, env_conf, terraform_platform_modules_version_override
    ):
        """
        Terraform platform modules version can be defined as an override, within
        the config, or defaulted. An override is always prioritied, followed by
        config version.

        Returns:
            string: version by priority
        """
        if terraform_platform_modules_version_override:
            return terraform_platform_modules_version_override

        config_version = env_conf.get("versions", {}).get("terraform-platform-modules")

        if config_version:
            return config_version

        return DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
