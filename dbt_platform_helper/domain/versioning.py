import os

from dbt_platform_helper.constants import CODEBASE_PIPELINE_MODULE_PATH
from dbt_platform_helper.constants import ENVIRONMENT_PIPELINE_MODULE_PATH
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_OVERRIDE_KEY
from dbt_platform_helper.constants import (
    TERRAFORM_CODEBASE_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR,
)
from dbt_platform_helper.constants import (
    TERRAFORM_ENVIRONMENT_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR,
)
from dbt_platform_helper.constants import (
    TERRAFORM_EXTENSIONS_MODULE_SOURCE_OVERRIDE_ENV_VAR,
)
from dbt_platform_helper.entities.semantic_version import (
    IncompatibleMajorVersionException,
)
from dbt_platform_helper.entities.semantic_version import (
    IncompatibleMinorVersionException,
)
from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.environment_variable import (
    EnvironmentVariableProvider,
)
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.version import AWSCLIInstalledVersionProvider
from dbt_platform_helper.providers.version import CopilotInstalledVersionProvider
from dbt_platform_helper.providers.version import GithubLatestVersionProvider
from dbt_platform_helper.providers.version import InstalledVersionProvider
from dbt_platform_helper.providers.version import PyPiLatestVersionProvider
from dbt_platform_helper.providers.version import VersionProvider
from dbt_platform_helper.providers.version_status import VersionStatus


def running_as_installed_package():
    return "site-packages" in __file__


def allow_override_of_versioning_checks_fn():
    return not running_as_installed_package() or "PLATFORM_TOOLS_SKIP_VERSION_CHECK" in os.environ


class PlatformHelperVersionNotFoundException(PlatformException):
    def __init__(self, message=None):
        super().__init__(message or "Platform helper version could not be resolved.")


class PlatformHelperVersioning:
    def __init__(
        self,
        io: ClickIOProvider = ClickIOProvider(),
        config_provider: ConfigProvider = ConfigProvider(),
        environment_variable_provider: EnvironmentVariableProvider = EnvironmentVariableProvider(),
        latest_version_provider: VersionProvider = PyPiLatestVersionProvider,
        installed_version_provider: InstalledVersionProvider = InstalledVersionProvider(),
        allow_override_of_versioning_checks: bool = None,
        platform_helper_version_override: str = None,
    ):
        self.io = io
        self.config_provider = config_provider
        self.latest_version_provider = latest_version_provider
        self.installed_version_provider = installed_version_provider
        self.allow_override_of_versioning_checks = (
            allow_override_of_versioning_checks
            if allow_override_of_versioning_checks is not None
            else allow_override_of_versioning_checks_fn()
        )
        self.environment_variable_provider = environment_variable_provider
        self.platform_helper_version_override = platform_helper_version_override

    def is_auto(self):
        platform_config = self.config_provider.load_unvalidated_config_file()
        default_version = platform_config.get("default_versions", {}).get("platform-helper")
        return default_version == "auto"

    def get_required_version(self) -> str:
        if self.is_auto():
            return str(self.get_version_status().latest)
        else:
            return self.get_default_version()

    def _check_environment_is_configured_for_auto_versioning_within_a_pipeline(self):
        platform_helper_version_is_set_in_environment = self.environment_variable_provider.get(
            PLATFORM_HELPER_VERSION_OVERRIDE_KEY
        ) or self.environment_variable_provider.get("PLATFORM_HELPER_VERSION")
        modules_override_is_set_in_environment = (
            self.environment_variable_provider.get(
                TERRAFORM_EXTENSIONS_MODULE_SOURCE_OVERRIDE_ENV_VAR
            )
            or self.environment_variable_provider.get(
                TERRAFORM_CODEBASE_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR
            )
            or self.environment_variable_provider.get(
                TERRAFORM_ENVIRONMENT_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR
            )
        )
        if platform_helper_version_is_set_in_environment and modules_override_is_set_in_environment:
            return
        else:
            message = "You are on managed upgrades. Generate commands should only be running inside a pipeline environment."
            if self.allow_override_of_versioning_checks:
                self.io.warn(message)
                self.io.info("Bypassing versioning enforcement")
            else:
                self.io.abort_with_error(message)

    def check_platform_helper_version_mismatch(self):
        if self.is_auto():
            self._check_environment_is_configured_for_auto_versioning_within_a_pipeline()

        version_status = self.get_version_status()
        required_version = self.get_required_version()

        if SemanticVersion.is_semantic_version(required_version):
            required_version_semver = SemanticVersion.from_string(required_version)

            if not version_status.installed == required_version_semver:
                message = (
                    f"WARNING: You are running platform-helper v{version_status.installed} against "
                    f"v{required_version_semver} required by the project. Running anything besides the version required by the project may result in unpredictable and destructive changes."
                )
                self.io.warn(message)

    def check_if_needs_update(self):
        if self.allow_override_of_versioning_checks:
            return

        version_status = self.get_version_status()

        message = (
            f"You are running platform-helper v{version_status.installed}, upgrade to "
            f"v{version_status.latest} by running run `pip install "
            "--upgrade dbt-platform-helper`."
        )

        try:
            version_status.installed.validate_compatibility_with(version_status.latest)
        except IncompatibleMajorVersionException:
            self.io.error(message)
        except IncompatibleMinorVersionException:
            self.io.warn(message)

    def get_version_status(self) -> VersionStatus:
        locally_installed_version = self.installed_version_provider.get_semantic_version(
            "dbt-platform-helper"
        )

        latest_release = self.latest_version_provider.get_semantic_version("dbt-platform-helper")

        return VersionStatus(installed=locally_installed_version, latest=latest_release)

    def get_default_version(self):
        return (
            self.config_provider.load_unvalidated_config_file()
            .get("default_versions", {})
            .get("platform-helper")
        )

    def get_template_version(self):
        if self.is_auto():
            return self.environment_variable_provider.get(PLATFORM_HELPER_VERSION_OVERRIDE_KEY)
        if self.platform_helper_version_override:
            return self.platform_helper_version_override
        platform_helper_env_override = self.environment_variable_provider.get(
            PLATFORM_HELPER_VERSION_OVERRIDE_KEY
        )
        if platform_helper_env_override:
            return platform_helper_env_override

        return self.get_default_version()

    def get_pinned_version(self):
        if self.is_auto():
            return self.environment_variable_provider.get(PLATFORM_HELPER_VERSION_OVERRIDE_KEY)

        return None

    def _get_pipeline_modules_source(self, pipeline_module_path: str, override_env_var_key: str):
        pipeline_module_override = self.environment_variable_provider.get(override_env_var_key)

        if pipeline_module_override:
            return pipeline_module_override

        if self.platform_helper_version_override:
            return f"{pipeline_module_path}{self.platform_helper_version_override}"

        platform_helper_env_override = self.environment_variable_provider.get(
            PLATFORM_HELPER_VERSION_OVERRIDE_KEY
        )

        if platform_helper_env_override:
            return f"{pipeline_module_path}{platform_helper_env_override}"

        return f"{pipeline_module_path}{self.get_required_version()}"

    def get_environment_pipeline_modules_source(self):
        return self._get_pipeline_modules_source(
            ENVIRONMENT_PIPELINE_MODULE_PATH,
            TERRAFORM_ENVIRONMENT_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR,
        )

    def get_codebase_pipeline_modules_source(self):
        return self._get_pipeline_modules_source(
            CODEBASE_PIPELINE_MODULE_PATH,
            TERRAFORM_CODEBASE_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR,
        )

    def get_extensions_module_source(self):
        return self.environment_variable_provider.get(
            TERRAFORM_EXTENSIONS_MODULE_SOURCE_OVERRIDE_ENV_VAR
        )


class AWSVersioning:
    def __init__(
        self,
        latest_version_provider: VersionProvider = None,
        installed_version_provider: VersionProvider = None,
    ):
        self.latest_version_provider = latest_version_provider or GithubLatestVersionProvider
        self.installed_version_provider = (
            installed_version_provider or AWSCLIInstalledVersionProvider
        )

    def get_version_status(self) -> VersionStatus:
        return VersionStatus(
            self.installed_version_provider.get_semantic_version(),
            self.latest_version_provider.get_semantic_version("aws/aws-cli", True),
        )


class CopilotVersioning:
    def __init__(
        self,
        latest_version_provider: VersionProvider = None,
        installed_version_provider: VersionProvider = None,
    ):
        self.latest_version_provider = latest_version_provider or GithubLatestVersionProvider
        self.installed_version_provider = (
            installed_version_provider or CopilotInstalledVersionProvider
        )

    def get_version_status(self) -> VersionStatus:
        return VersionStatus(
            self.installed_version_provider.get_semantic_version(),
            self.latest_version_provider.get_semantic_version("aws/copilot-cli"),
        )
