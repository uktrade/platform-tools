import os

from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_OVERRIDE_KEY
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMajorVersionException,
)
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMinorVersionException,
)
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.version import AWSCLIInstalledVersionProvider
from dbt_platform_helper.providers.version import CopilotInstalledVersionProvider
from dbt_platform_helper.providers.version import GithubLatestVersionProvider
from dbt_platform_helper.providers.version import InstalledVersionProvider
from dbt_platform_helper.providers.version import PyPiLatestVersionProvider
from dbt_platform_helper.providers.version import VersionProvider
from dbt_platform_helper.providers.version_status import VersionStatus


def running_as_installed_package():
    return "site-packages" in __file__


def skip_version_checks():
    return not running_as_installed_package() or "PLATFORM_TOOLS_SKIP_VERSION_CHECK" in os.environ


class PlatformHelperVersionNotFoundException(PlatformException):
    def __init__(self, message=None):
        super().__init__(message or "Platform helper version could not be resolved.")


class PlatformHelperVersioning:
    def __init__(
        self,
        io: ClickIOProvider = ClickIOProvider(),
        config_provider: ConfigProvider = ConfigProvider(),
        latest_version_provider: VersionProvider = PyPiLatestVersionProvider,
        installed_version_provider: InstalledVersionProvider = InstalledVersionProvider(),
        skip_versioning_checks: bool = None,
        platform_helper_version_override: str = None,
    ):
        self.io = io
        self.config_provider = config_provider
        self.latest_version_provider = latest_version_provider
        self.installed_version_provider = installed_version_provider
        self.skip_versioning_checks = (
            skip_versioning_checks if skip_versioning_checks is not None else skip_version_checks()
        )
        self.platform_helper_version_override = platform_helper_version_override or os.environ.get(
            PLATFORM_HELPER_VERSION_OVERRIDE_KEY
        )

    def get_required_version(self):
        required_version = self._resolve_required_version()
        self.io.info(required_version)
        return required_version

    # Used in the generate command
    def check_platform_helper_version_mismatch(self):
        if self.skip_versioning_checks:
            return

        version_status = self.get_version_status()
        required_version = self._resolve_required_version()

        if SemanticVersion.is_semantic_version(required_version):
            required_version_semver = SemanticVersion.from_string(required_version)

            if not version_status.installed == required_version_semver:
                message = (
                    f"WARNING: You are running platform-helper v{version_status.installed} against "
                    f"v{required_version_semver} specified for the project."
                )
                self.io.warn(message)

    def check_if_needs_update(self):
        if self.skip_versioning_checks:
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

    def _resolve_required_version(self) -> str:
        platform_config = self.config_provider.load_and_validate_platform_config()

        platform_helper_version = platform_config.get("default_versions", {}).get("platform-helper")

        if self.platform_helper_version_override:
            platform_helper_version = self.platform_helper_version_override

        return platform_helper_version


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
