from copy import deepcopy
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

from schema import SchemaError

from dbt_platform_helper.constants import CURRENT_PLATFORM_CONFIG_SCHEMA_VERSION
from dbt_platform_helper.constants import FIRST_UPGRADABLE_PLATFORM_HELPER_MAJOR_VERSION
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.config_validator import ConfigValidatorError
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.platform_config_schema import PlatformConfigSchema
from dbt_platform_helper.providers.yaml_file import FileNotFoundException
from dbt_platform_helper.providers.yaml_file import FileProviderException
from dbt_platform_helper.providers.yaml_file import YamlFileProvider

MISSING_SCHEMA_VERSION_ERROR = """Please upgrade to v13 following the instructions in https://platform.readme.trade.gov.uk/ and then upgrade to
    version {platform_helper_version} by running: `platform-helper config migrate.
(If you cannot upgrade immediately then downgrade your platform-helper version using 'pip install --upgrade dbt-platform-helper==12.0.0')"""
PLEASE_UPGRADE_TO_V13_MESSAGE = "Please upgrade to v13 following the instructions in https://platform.readme.trade.gov.uk/ and\n    then run 'platform-helper config migrate' to upgrade to the current version."
SCHEMA_VERSION_MESSAGE = """Installed version: platform-helper: {platform_helper_version} (schema version: {schema_version})
'platform-config.yml' version: platform-helper: {config_platform_helper_version} (schema version: {config_schema_version})"""


class ConfigProvider:
    def __init__(
        self,
        config_validator: ConfigValidator = None,
        file_provider: YamlFileProvider = None,
        io: ClickIOProvider = None,
        current_platform_config_schema_version: int = None,
        current_platform_helper_version: str = None,
    ):
        self.config = {}
        self.validator = config_validator or ConfigValidator()
        self.io = io or ClickIOProvider()
        self.file_provider = file_provider or YamlFileProvider
        self.current_platform_config_schema_version = (
            current_platform_config_schema_version or CURRENT_PLATFORM_CONFIG_SCHEMA_VERSION
        )
        self.current_platform_helper_version = current_platform_helper_version or version(
            "dbt-platform-helper"
        )

    # TODO refactor so that apply_environment_defaults isn't set, discarded and set again
    def get_enriched_config(self):
        return self.apply_environment_defaults(self.load_and_validate_platform_config())

    def _validate_platform_config(self):
        PlatformConfigSchema.schema().validate(self.config)
        # TODO= logically this isn't validation but loading + parsing, to move.
        # also, we apply defaults but discard that data.  Should we just apply
        # defaults to config returned by load_and_validate
        enriched_config = ConfigProvider.apply_environment_defaults(self.config)

        try:
            self.validator.run_validations(enriched_config)
        except ConfigValidatorError as exc:
            self.io.abort_with_error(f"Config validation has failed.\n{str(exc)}")

    def load_and_validate_platform_config(self, path=PLATFORM_CONFIG_FILE):
        try:
            self.config = self.file_provider.load(path)
        except FileNotFoundException as e:
            self.io.abort_with_error(
                f"{e} Please check it exists and you are in the root directory of your deployment project."
            )
        except FileProviderException as e:
            self.io.abort_with_error(f"Error loading configuration from {path}: {e}")

        self._validate_schema_version()

        try:
            self._validate_platform_config()
        except SchemaError as e:
            self.io.abort_with_error(f"Schema error in {path}. {e}")

        return self.config

    def _abort_due_to_schema_version_error(self, config_description: str, action_required: str):
        self.io.abort_with_error(
            "\n".join(
                [
                    config_description,
                    "",
                    action_required,
                ]
            )
        )

    def _validate_schema_version(self):
        platform_config_schema_version = self.config.get("schema_version")
        platform_helper_default_version = self.config.get("default_versions", {}).get(
            "platform-helper", ""
        )
        header = SCHEMA_VERSION_MESSAGE.format(
            platform_helper_version=self.current_platform_helper_version,
            schema_version=self.current_platform_config_schema_version,
            config_platform_helper_version=(
                platform_helper_default_version if platform_helper_default_version else "N/A"
            ),
            config_schema_version=(
                platform_config_schema_version if platform_config_schema_version else "N/A"
            ),
        )

        if platform_config_schema_version:
            self._handle_schema_version_mismatch(platform_config_schema_version, header)
        else:
            self._handle_missing_schema_version(platform_helper_default_version, header)

    def _handle_schema_version_mismatch(self, platform_config_schema_version: int, header: str):
        if platform_config_schema_version < self.current_platform_config_schema_version:
            self._abort_due_to_schema_version_error(
                header,
                "Please upgrade your platform-config.yml by running 'platform-helper config migrate'.",
            )
        elif platform_config_schema_version > self.current_platform_config_schema_version:
            self._abort_due_to_schema_version_error(
                header,
                f"Please update your platform-helper to a version that supports schema_version: {platform_config_schema_version}.",
            )
        # else the schema_version is the correct one so continue.

    def _handle_missing_schema_version(self, platform_helper_default_version: str, header: str):
        version_parts = platform_helper_default_version.split(".")
        major_version = int(version_parts[0]) if version_parts[0] else None
        if not major_version:
            self._abort_due_to_schema_version_error(
                header,
                PLEASE_UPGRADE_TO_V13_MESSAGE,
            )
        if major_version and major_version == FIRST_UPGRADABLE_PLATFORM_HELPER_MAJOR_VERSION:
            self._abort_due_to_schema_version_error(
                header,
                f"Please upgrade your platform-config.yml to be compatible with {self.current_platform_helper_version} by running: 'platform-helper config migrate'.",
            )
        elif major_version and major_version < FIRST_UPGRADABLE_PLATFORM_HELPER_MAJOR_VERSION:
            self._abort_due_to_schema_version_error(
                header,
                MISSING_SCHEMA_VERSION_ERROR.format(
                    platform_helper_version=self.current_platform_helper_version
                ),
            )
        # if major_version and major_version > FIRST_UPGRADABLE_PLATFORM_HELPER_MAJOR_VERSION then
        # the platform-config.yml is malformed and so should progress to validation if appropriate.

    def load_unvalidated_config_file(self, path=PLATFORM_CONFIG_FILE):
        try:
            return self.file_provider.load(path)
        except FileProviderException:
            return {"schema_version": self.current_platform_config_schema_version}

    # TODO remove function and push logic to where this is called.
    # removed usage from config domain, code is very generic and doesn't require the overhead of a function
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

        config.get("default_versions", {})

        def combine_env_data(data):
            return {
                **env_defaults,
                **data,
            }

        defaulted_envs = {
            env_name: combine_env_data(env_data)
            for env_name, env_data in without_defaults_entry.items()
        }

        enriched_config["environments"] = defaulted_envs

        return enriched_config

    def write_platform_config(self, new_platform_config):
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"# Generated by platform-helper {self.current_platform_helper_version} / {current_date}.\n\n"
        self.file_provider.write(PLATFORM_CONFIG_FILE, new_platform_config, message)
