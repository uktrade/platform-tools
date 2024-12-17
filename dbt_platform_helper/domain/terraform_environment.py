from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.template import setup_templates
from dbt_platform_helper.utils.validation import load_and_validate_platform_config


# TODO this is just to illustrate what the config provider might look like and how it's injected
class TempPlatformConfigProvider:
    def __init__(self):
        self.config = self._load_and_validate_config()

    def _load_and_validate_config(self):
        return load_and_validate_platform_config()

    def get_environment_configuration(self, environment_name):
        full_config = apply_environment_defaults(self.config)
        return full_config["environments"][environment_name]

    def get_terraform_platform_modules_version(self, environment_name):
        environment_config = self.get_environment_configuration(environment_name)
        return environment_config.get("versions", {}).get("terraform-platform-modules")


class TerraformEnvironment:
    def __init__(self, config_provider, echo):
        self.echo = echo
        self.config_provider = config_provider

    def generate(self, environment_name, terraform_platform_modules_version):
        env_config = self.config_provider.get_environment_configuration(environment_name)
        env_template = setup_templates().get_template("environments/main.tf")
        version = self._determine_terraform_platform_modules_version(
            environment_name, terraform_platform_modules_version
        )

        contents = env_template.render(
            {
                "application": self.config_provider.config["application"],
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

    def _determine_terraform_platform_modules_version(
        self, environment_name, terraform_platform_modules_version_override
    ):
        version_preference_order = [
            terraform_platform_modules_version_override,
            self.config_provider.get_terraform_platform_modules_version(environment_name),
            DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION,
        ]
        return [version for version in version_preference_order if version][0]
