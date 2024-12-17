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

    def generate(self, conf, name, terraform_platform_modules_version):
        env_config = apply_environment_defaults(conf)["environments"][name]
        self._generate_terraform_environment_manifests(
            conf["application"], name, env_config, terraform_platform_modules_version
        )

    def _generate_terraform_environment_manifests(
        self, application, env, env_config, cli_terraform_platform_modules_version
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

        self.echo(mkfile(".", f"terraform/environments/{env}/main.tf", contents, overwrite=True))
