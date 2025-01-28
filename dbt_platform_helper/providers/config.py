from copy import deepcopy
from pathlib import Path

from schema import SchemaError

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.domain.config_validator import ConfigValidator
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.platform_config_schema import PlatformConfigSchema
from dbt_platform_helper.providers.yaml_file import FileNotFoundException
from dbt_platform_helper.providers.yaml_file import FileProviderException
from dbt_platform_helper.providers.yaml_file import YamlFileProvider


class ConfigProvider:
    def __init__(
        self,
        config_validator: ConfigValidator = None,
        file_provider: YamlFileProvider = None,
        io: ClickIOProvider = None,
    ):
        self.config = {}
        self.validator = config_validator or ConfigValidator()
        self.io = io or ClickIOProvider()
        self.file_provider = file_provider or YamlFileProvider

    # TODO refactor so that apply_environment_defaults isn't set, discarded and set again
    def get_enriched_config(self):
        return self.apply_environment_defaults(self.load_and_validate_platform_config())

    def _validate_platform_config(self):
        PlatformConfigSchema.schema().validate(self.config)

        # TODO= logically this isn't validation but loading + parsing, to move.
        # also, we apply defaults but discard that data.  Should we just apply
        # defaults to config returned by load_and_validate
        enriched_config = ConfigProvider.apply_environment_defaults(self.config)
        self.validator.run_validations(enriched_config)

    def load_and_validate_platform_config(self, path=PLATFORM_CONFIG_FILE):
        try:
            self.config = self.file_provider.load(path)
        except FileNotFoundException as e:
            self.io.abort_with_error(
                f"{e} Please check it exists and you are in the root directory of your deployment project."
            )
        except FileProviderException as e:
            self.io.abort_with_error(f"Error loading configuration from {path}: {e}")

        try:
            self._validate_platform_config()
        except SchemaError as e:
            self.io.abort_with_error(f"Schema error in {path}. {e}")

        return self.config

    # TODO this general function should be moved out of ConfigProvider
    def config_file_check(self, path=PLATFORM_CONFIG_FILE):
        if not Path(path).exists():
            self.io.abort_with_error(
                f"`{path}` is missing. "
                "Please check it exists and you are in the root directory of your deployment project."
            )

    @staticmethod
    def apply_environment_defaults(config):
        if "environments" not in config:
            return config

        enriched_config = deepcopy(config)

        environments = enriched_config["environments"]
        env_defaults = environments.get("*", {})
        without_defaults_entry = {
            name: data if data else {} for name, data in environments.items() if name != "*"
        }

        default_versions = config.get("default_versions", {})

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
