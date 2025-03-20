import os

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
from dbt_platform_helper.providers.version import DeprecatedVersionFileVersionProvider
from dbt_platform_helper.providers.version import GithubLatestVersionProvider
from dbt_platform_helper.providers.version import InstalledVersionProvider
from dbt_platform_helper.providers.version import PyPiLatestVersionProvider
from dbt_platform_helper.providers.version import VersionProvider
from dbt_platform_helper.providers.version_status import PlatformHelperVersionStatus
from dbt_platform_helper.providers.version_status import VersionStatus
from dbt_platform_helper.providers.yaml_file import YamlFileProvider


def running_as_installed_package():
    return "site-packages" in __file__


def skip_version_checks():
    return not running_as_installed_package() or "PLATFORM_TOOLS_SKIP_VERSION_CHECK" in os.environ


class PlatformHelperVersionNotFoundException(PlatformException):
    def __init__(self):
        super().__init__(f"""Platform helper version could not be resolved.""")


class PlatformHelperVersioning:
    def __init__(
        self,
        io: ClickIOProvider = ClickIOProvider(),
        version_file_version_provider: DeprecatedVersionFileVersionProvider = DeprecatedVersionFileVersionProvider(
            YamlFileProvider
        ),
        config_provider: ConfigProvider = ConfigProvider(),
        latest_version_provider: VersionProvider = PyPiLatestVersionProvider,
        installed_version_provider: InstalledVersionProvider = InstalledVersionProvider(),
        skip_versioning_checks: bool = None,
    ):
        self.io = io
        self.version_file_version_provider = version_file_version_provider
        self.config_provider = config_provider
        self.latest_version_provider = latest_version_provider
        self.installed_version_provider = installed_version_provider
        self.skip_versioning_checks = (
            skip_versioning_checks if skip_versioning_checks is not None else skip_version_checks()
        )

    def get_required_version(self, pipeline=None):
        version_status = self._get_version_status()
        self.io.process_messages(version_status.validate())
        required_version = self._resolve_required_version(pipeline, version_status)
        self.io.info(required_version)
        return required_version

    # Used in the generate command
    def check_platform_helper_version_mismatch(self):
        if self.skip_versioning_checks:
            return

        version_status = self._get_version_status()
        self.io.process_messages(version_status.validate())

        required_version = SemanticVersion.from_string(
            self._resolve_required_version(version_status=version_status)
        )

        if not version_status.installed == required_version:
            message = (
                f"WARNING: You are running platform-helper v{version_status.installed} against "
                f"v{required_version} specified for the project."
            )
            self.io.warn(message)

    def check_if_needs_update(self):
        if self.skip_versioning_checks:
            return

        version_status = self._get_version_status(include_project_versions=False)

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

    def _get_version_status(
        self,
        include_project_versions: bool = True,
    ) -> PlatformHelperVersionStatus:
        locally_installed_version = self.installed_version_provider.get_semantic_version(
            "dbt-platform-helper"
        )

        latest_release = self.latest_version_provider.get_semantic_version("dbt-platform-helper")

        if not include_project_versions:
            return PlatformHelperVersionStatus(
                installed=locally_installed_version,
                latest=latest_release,
            )

        platform_config_default, pipeline_overrides = None, {}

        platform_config = self.config_provider.load_unvalidated_config_file()

        if platform_config:
            platform_config_default = SemanticVersion.from_string(
                platform_config.get("default_versions", {}).get("platform-helper")
            )

            pipeline_overrides = {
                name: pipeline.get("versions", {}).get("platform-helper")
                for name, pipeline in platform_config.get("environment_pipelines", {}).items()
                if pipeline.get("versions", {}).get("platform-helper")
            }
        out = PlatformHelperVersionStatus(
            installed=locally_installed_version,
            latest=latest_release,
            deprecated_version_file=self.version_file_version_provider.get_semantic_version(),
            platform_config_default=platform_config_default,
            pipeline_overrides=pipeline_overrides,
        )

        return out

    def _resolve_required_version(
        self, pipeline: str = None, version_status: PlatformHelperVersionStatus = None
    ) -> str:
        pipeline_version = version_status.pipeline_overrides.get(pipeline)
        version_precedence = [
            pipeline_version,
            version_status.platform_config_default,
            version_status.deprecated_version_file,
        ]
        non_null_version_precedence = [
            f"{v}" if isinstance(v, SemanticVersion) else v for v in version_precedence if v
        ]

        out = non_null_version_precedence[0] if non_null_version_precedence else None

        if not out:
            raise PlatformHelperVersionNotFoundException

        return out


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
