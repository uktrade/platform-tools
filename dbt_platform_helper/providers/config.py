import os
from copy import deepcopy
from pathlib import Path

import click
import yaml
from schema import SchemaError
from yaml.parser import ParserError
from yamllint import linter
from yamllint.config import YamlLintConfig

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.providers.platform_config_schema import PlatformConfigSchema
from dbt_platform_helper.utils.messages import abort_with_error


class ConfigProvider:
    def __init__(self, config_validator, config=None, echo=click.secho):
        self.config = config or {}
        self.validator = config_validator
        self.echo = echo

    # TODO - this is to do with Yaml validation
    def lint_yaml_for_duplicate_keys(self, file_path: str, lint_config=None):
        if lint_config is None:
            lint_config = {"rules": {"key-duplicates": "enable"}}

        with open(file_path, "r") as yaml_file:
            file_contents = yaml_file.read()
            results = linter.run(file_contents, YamlLintConfig(yaml.dump(lint_config)))

        parsed_results = [
            "\t"
            + f"Line {result.line}: {result.message}".replace(" in mapping (key-duplicates)", "")
            for result in results
        ]

        return parsed_results

    def validate_platform_config(self):
        PlatformConfigSchema.schema().validate(self.config)

        # TODO= logically this isn't validation but loading + parsing, to move.
        enriched_config = self.apply_environment_defaults()
        self.validator.run_validations(enriched_config)

    def load_and_validate_platform_config(self, path=PLATFORM_CONFIG_FILE):
        self.config_file_check(path)
        try:
            self.config = yaml.safe_load(Path(path).read_text())

            duplicate_keys = self.lint_yaml_for_duplicate_keys(path)
            if duplicate_keys:
                abort_with_error(
                    "Duplicate keys found in platform-config:"
                    + os.linesep
                    + os.linesep.join(duplicate_keys)
                )
            self.validate_platform_config()
            return self.config
        except ParserError:
            abort_with_error(f"{PLATFORM_CONFIG_FILE} is not valid YAML")
        except SchemaError as e:
            abort_with_error(f"Schema error in {PLATFORM_CONFIG_FILE}. {e}")

    def config_file_check(self, path=PLATFORM_CONFIG_FILE):
        if not Path(path).exists():
            abort_with_error(
                f"`{PLATFORM_CONFIG_FILE}` is missing. "
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
