from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.template import setup_templates


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
    def __init__(self, echo):
        self.echo = echo

    def generate(self, config, environment_name, terraform_platform_modules_version):
        env_config = self._get_environment_configuration(config, environment_name)
        env_template = setup_templates().get_template("environments/main.tf")
        version = _determine_terraform_platform_modules_version(
            env_config, terraform_platform_modules_version
        )

        contents = env_template.render(
            {
                "application": config["application"],
                "environment": environment_name,
                "config": env_config,
                "terraform_platform_modules_version": version,
            }
        )

        self.echo(
            mkfile(
                ".", f"terraform/environments/{environment_name}/main.tf", contents, overwrite=True
            )
        )

    @staticmethod
    # TODO This should be in the config provider
    def _get_environment_configuration(config, environment_name):
        full_config = apply_environment_defaults(config)
        return full_config["environments"][environment_name]
