import click

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.utils.template import setup_templates


def _generate_terraform_environment_manifests(
    application, environment_name, env_config, cli_terraform_platform_modules_version
):
    env_template = setup_templates().get_template("environments/main.tf")

    terraform_platform_modules_version = _determine_terraform_platform_modules_version(
        env_config, cli_terraform_platform_modules_version
    )

    contents = env_template.render(
        {
            "application": application,
            "environment": environment_name,
            "config": env_config,
            "terraform_platform_modules_version": terraform_platform_modules_version,
        }
    )

    click.echo(
        FileProvider.mkfile(
            ".", f"terraform/environments/{environment_name}/main.tf", contents, overwrite=True
        )
    )


def _determine_terraform_platform_modules_version(
    env_conf, terraform_platform_modules_version_override
):
    env_conf_terraform_platform_modules_version = env_conf.get("versions", {}).get(
        "terraform-platform-modules"
    )
    version_preference_order = [
        terraform_platform_modules_version_override,
        env_conf_terraform_platform_modules_version,
        DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION,
    ]
    return [version for version in version_preference_order if version][0]


class TerraformEnvironment:
    def __init__(self, config_provider):
        self.config_provider = config_provider

    def generate(self, environment_name, terraform_platform_modules_version):
        config = self.config_provider.load_and_validate_platform_config()
        enriched_config = self.config_provider.apply_environment_defaults(config)

        env_config = enriched_config["environments"][environment_name]
        _generate_terraform_environment_manifests(
            config["application"], environment_name, env_config, terraform_platform_modules_version
        )
