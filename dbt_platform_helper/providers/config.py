import os
from pathlib import Path

import click
import yaml
from schema import SchemaError
from yaml.parser import ParserError
from yamllint import config
from yamllint import linter

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.providers.platform_config_schema import PlatformConfigSchema
from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.messages import abort_with_error


class ConfigProvider:
    def __init__(self, config_validator, config=None):
        self.config = config or {}
        self.validator = config_validator

    def get_config(self, path=PLATFORM_CONFIG_FILE):
        return self.load_and_validate_platform_config(self, path, False)

    def lint_yaml_for_duplicate_keys(self, file_path: str, lint_config=None):
        if lint_config is None:
            lint_config = {"rules": {"key-duplicates": "enable"}}

        yaml_config = config.YamlLintConfig(yaml.dump(lint_config))

        with open(file_path, "r") as yaml_file:
            file_contents = yaml_file.read()
            results = linter.run(file_contents, yaml_config)

        parsed_results = [
            "\t"
            + f"Line {result.line}: {result.message}".replace(" in mapping (key-duplicates)", "")
            for result in results
        ]

        return parsed_results

    def validate_platform_config(self):
        PlatformConfigSchema.schema().validate(self.config)

        # TODO= logically this isn't validation but loading + parsing, to move.
        enriched_config = apply_environment_defaults(self.config)
        self.validator.run_validations(enriched_config)

    def load_and_validate_platform_config(
        self, path=PLATFORM_CONFIG_FILE, disable_file_check=False
    ):
        if not disable_file_check:
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
        platform_config_exists = Path(path).exists()

        if not platform_config_exists:
            click.secho(
                f"`{PLATFORM_CONFIG_FILE}` is missing. "
                "Please check it exists and you are in the root directory of your deployment project."
            )
            exit(1)
