import click

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.template import setup_templates


def _generate_terraform_environment_manifests(
    application, env, env_config, cli_terraform_platform_modules_version
):
    env_template = setup_templates().get_template("environments/main.tf")

    terraform_platform_modules_version = _determine_terraform_platform_modules_version(
        env_config, cli_terraform_platform_modules_version
    )

    contents = env_template.render(
        {
            "application": application,
            "environment": env,
            "config": env_config,
            "terraform_platform_modules_version": terraform_platform_modules_version,
        }
    )

    click.echo(mkfile(".", f"terraform/environments/{env}/main.tf", contents, overwrite=True))


def _determine_terraform_platform_modules_version(env_conf, cli_terraform_platform_modules_version):
    cli_terraform_platform_modules_version = cli_terraform_platform_modules_version
    env_conf_terraform_platform_modules_version = env_conf.get("versions", {}).get(
        "terraform-platform-modules"
    )
    version_preference_order = [
        cli_terraform_platform_modules_version,
        env_conf_terraform_platform_modules_version,
        DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION,
    ]
    return [version for version in version_preference_order if version][0]


class TerraformEnvironment:
    def __init__(self, config_provider):
        self.config_provider = config_provider

    def generate(self, name, terraform_platform_modules_version):
        config = self.config_provider.load_and_validate_platform_config()
        enriched_config = self.config_provider.apply_environment_defaults(config)

        env_config = enriched_config["environments"][name]
        _generate_terraform_environment_manifests(
            config["application"], name, env_config, terraform_platform_modules_version
        )
