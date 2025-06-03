from copy import deepcopy
from datetime import datetime
from pathlib import Path

from schema import SchemaError

from dbt_platform_helper.constants import FIRST_UPGRADABLE_PLATFORM_HELPER_MAJOR_VERSION
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_CONFIG_SCHEMA_VERSION
from dbt_platform_helper.constants import PLATFORM_HELPER_PACKAGE_NAME
from dbt_platform_helper.entities.platform_config_schema import PlatformConfigSchema
from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.config_validator import ConfigValidatorError
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.version import InstalledVersionProvider
from dbt_platform_helper.providers.yaml_file import FileNotFoundException
from dbt_platform_helper.providers.yaml_file import FileProviderException
from dbt_platform_helper.providers.yaml_file import YamlFileProvider

SCHEMA_VERSION_MESSAGE = """Installed version: platform-helper: {installed_platform_helper_version} (schema version: {installed_schema_version})
'platform-config.yml' version: platform-helper: {config_platform_helper_version} (schema version: {config_schema_version})"""
PLEASE_UPGRADE_TO_V13_MESSAGE = """Please ensure that you have already upgraded to platform-helper 13, following the instructions in https://platform.readme.trade.gov.uk/reference/upgrading-platform-helper/.

Then upgrade platform-helper to version {installed_platform_helper_version} and run 'platform-helper config migrate' to upgrade the configuration to the current schema version."""


class ConfigProvider:
    def __init__(
        self,
        config_validator: ConfigValidator = ConfigValidator(),
        file_provider: YamlFileProvider = YamlFileProvider,
        io: ClickIOProvider = ClickIOProvider(),
        schema_version_for_installed_platform_helper: int = PLATFORM_CONFIG_SCHEMA_VERSION,
        installed_version_provider: InstalledVersionProvider = InstalledVersionProvider,
    ):
        self.config = {}
        self.validator = config_validator
        self.io = io
        self.file_provider = file_provider
        self.schema_version_for_installed_platform_helper = (
            schema_version_for_installed_platform_helper
        )
        self.installed_version_provider = installed_version_provider

    # TODO: DBTP-1964: refactor so that apply_environment_defaults isn't set, discarded and set again
    def get_enriched_config(self):
        return self.apply_environment_defaults(self.load_and_validate_platform_config())

    def _validate_platform_config(self):
        PlatformConfigSchema.schema().validate(self.config)
        # TODO: DBTP-1964: = logically this isn't validation but loading + parsing, to move.
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
        config_schema_version = self.config.get("schema_version")
        config_platform_helper_version = self.config.get("default_versions", {}).get(
            "platform-helper", ""
        )
        header = SCHEMA_VERSION_MESSAGE.format(
            installed_platform_helper_version=self._installed_platform_helper_version(),
            installed_schema_version=self.schema_version_for_installed_platform_helper,
            config_platform_helper_version=(
                config_platform_helper_version if config_platform_helper_version else "N/A"
            ),
            config_schema_version=(config_schema_version if config_schema_version else "N/A"),
        )

        if config_schema_version:
            self._handle_schema_version_mismatch(config_schema_version, header)
        else:
            self._handle_missing_schema_version(config_platform_helper_version, header)

    def _handle_schema_version_mismatch(self, platform_config_schema_version: int, header: str):
        platform_config_schema_version_is_old = (
            platform_config_schema_version < self.schema_version_for_installed_platform_helper
        )
        installed_platform_helper_is_old = (
            platform_config_schema_version > self.schema_version_for_installed_platform_helper
        )

        if platform_config_schema_version_is_old:
            self._abort_due_to_schema_version_error(
                header,
                "Please upgrade your platform-config.yml by running 'platform-helper config migrate'.",
            )
        elif installed_platform_helper_is_old:
            self._abort_due_to_schema_version_error(
                header,
                f"Please update your platform-helper to a version that supports schema_version: {platform_config_schema_version}.",
            )
        # else the schema_version is the correct one so continue.

    def _handle_missing_schema_version(self, config_platform_helper_version: str, header: str):
        config_p_h_version_semver = SemanticVersion.from_string(config_platform_helper_version)
        major_version = config_p_h_version_semver and config_p_h_version_semver.major
        platform_config_is_old_but_supported_by_migrations = (
            major_version and major_version == FIRST_UPGRADABLE_PLATFORM_HELPER_MAJOR_VERSION
        )
        platform_config_is_old = (
            major_version and major_version < FIRST_UPGRADABLE_PLATFORM_HELPER_MAJOR_VERSION
        )
        platform_config_is_really_old = not major_version
        installed_platform_helper_version = self._installed_platform_helper_version()

        if platform_config_is_old_but_supported_by_migrations:
            self._abort_due_to_schema_version_error(
                header,
                f"Please upgrade your platform-config.yml to be compatible with {installed_platform_helper_version} by running: 'platform-helper config migrate'.",
            )
        elif platform_config_is_old or platform_config_is_really_old:
            self._abort_due_to_schema_version_error(
                header,
                PLEASE_UPGRADE_TO_V13_MESSAGE.format(
                    installed_platform_helper_version=installed_platform_helper_version,
                ),
            )
        # if major_version and major_version > FIRST_UPGRADABLE_PLATFORM_HELPER_MAJOR_VERSION then
        # the platform-config.yml is malformed and so should progress to validation if appropriate.

    def load_unvalidated_config_file(self, path=PLATFORM_CONFIG_FILE):
        try:
            return self.file_provider.load(path)
        except FileProviderException:
            return {}

    # TODO: DBTP-1888: remove function and push logic to where this is called.
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
        message = f"# Generated by platform-helper {self._installed_platform_helper_version()} / {current_date}.\n\n"
        self.file_provider.write(PLATFORM_CONFIG_FILE, new_platform_config, message)

    def _installed_platform_helper_version(self) -> str:
        return str(
            self.installed_version_provider.get_semantic_version(PLATFORM_HELPER_PACKAGE_NAME)
        )
