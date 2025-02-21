import os
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
from pathlib import Path

from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMajorVersionException,
)
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMinorVersionException,
)
from dbt_platform_helper.providers.semantic_version import PlatformHelperVersionStatus
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.version import PyPiVersionProvider
from dbt_platform_helper.providers.yaml_file import FileProviderException
from dbt_platform_helper.providers.yaml_file import YamlFileProvider


class PlatformHelperVersioning:
    def __init__(
        self,
        io: ClickIOProvider = ClickIOProvider(),
        file_provider: FileProvider = YamlFileProvider,
        config_provider: ConfigProvider = ConfigProvider(),
        pypi_provider: PyPiVersionProvider = PyPiVersionProvider,
    ):
        self.io = io
        self.file_provider = file_provider
        self.config_provider = config_provider
        self.pypi_provider = pypi_provider

    def get_status(
        self,
        include_project_versions=True,
    ) -> PlatformHelperVersionStatus:
        try:
            locally_installed_version = SemanticVersion.from_string(version("dbt-platform-helper"))
        except PackageNotFoundError:
            locally_installed_version = None

        latest_release = self.pypi_provider.get_latest_version("dbt-platform-helper")

        if not include_project_versions:
            return PlatformHelperVersionStatus(
                local=locally_installed_version,
                latest=latest_release,
            )

        deprecated_version_file = Path(PLATFORM_HELPER_VERSION_FILE)
        try:
            loaded_version = self.file_provider.load(deprecated_version_file)
            version_from_file = SemanticVersion.from_string(loaded_version)
        except FileProviderException:
            version_from_file = None

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
            local=locally_installed_version,
            latest=latest_release,
            deprecated_version_file=version_from_file,
            platform_config_default=platform_config_default,
            pipeline_overrides=pipeline_overrides,
        )

        return out

    def check_if_needs_update(self):
        if not running_as_installed_package() or "PLATFORM_TOOLS_SKIP_VERSION_CHECK" in os.environ:
            return

        version_status = self.get_status(include_project_versions=False)

        message = (
            f"You are running platform-helper v{version_status.local}, upgrade to "
            f"v{version_status.latest} by running run `pip install "
            "--upgrade dbt-platform-helper`."
        )

        try:
            version_status.local.validate_compatibility_with(version_status.latest)
        except IncompatibleMajorVersionException:
            self.io.error(message)
        except IncompatibleMinorVersionException:
            self.io.warn(message)


# TODO consolidate with the same function in versioning and given a home
def running_as_installed_package():
    return "site-packages" in __file__
