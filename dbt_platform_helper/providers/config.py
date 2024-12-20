from copy import deepcopy
from pathlib import Path

import click

from schema import SchemaError
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.providers.platform_config_schema import PlatformConfigSchema
from dbt_platform_helper.providers.yaml_file import YamlFileProvider
from dbt_platform_helper.providers.yaml_file import YamlFileProviderException
from dbt_platform_helper.utils.messages import abort_with_error


class ConfigProvider:
    def __init__(self, config_validator, echo=click.secho):
        self.config = {}
        self.validator = config_validator
        self.echo = echo
        self.yaml_file_provider = YamlFileProvider

    def validate_platform_config(self):
        PlatformConfigSchema.schema().validate(self.config)

        # TODO= logically this isn't validation but loading + parsing, to move.
        enriched_config = self.apply_environment_defaults()
        self.validator.run_validations(enriched_config)

    def load_and_validate_platform_config(self, path=PLATFORM_CONFIG_FILE):
        try:
            self.config = self.yaml_file_provider.load(path)
        except YamlFileProviderException as e:
            abort_with_error(f"Error loading configuration from {path}: {e}")

        try:
            self.validate_platform_config()
        except SchemaError as e:
            abort_with_error(f"Schema error in {path}. {e}")

        return self.config

    @staticmethod
    def config_file_check(path=PLATFORM_CONFIG_FILE):
        if not Path(path).exists():
            abort_with_error(
                f"`{path}` is missing. "
                "Please check it exists and you are in the root directory of your deployment project."
            )

    def apply_environment_defaults(self):
        if "environments" not in self.config:
            return self.config

        enriched_config = deepcopy(self.config)

        environments = enriched_config["environments"]
        env_defaults = environments.get("*", {})
        without_defaults_entry = {
            name: data if data else {} for name, data in environments.items() if name != "*"
        }

        default_versions = self.config.get("default_versions", {})

        def combine_env_data(data):
            return {
                **env_defaults,
                **data,
                "versions": {
                    **default_versions,
                    **env_defaults.get("versions", {}),
                    **data.get("versions", {}),
                },
            }

        defaulted_envs = {
            env_name: combine_env_data(env_data)
            for env_name, env_data in without_defaults_entry.items()
        }

        enriched_config["environments"] = defaulted_envs

        return enriched_config
