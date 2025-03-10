from abc import ABC
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
from pathlib import Path

import requests

from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.yaml_file import FileProviderException
from dbt_platform_helper.providers.yaml_file import YamlFileProvider


class InstalledVersionProviderException(PlatformException):
    pass


class InstalledToolNotFoundException(InstalledVersionProviderException):
    def __init__(
        self,
        tool_name: str,
    ):
        super().__init__(f"Package '{tool_name}' not found.")


class VersionProvider(ABC):
    pass


class InstalledVersionProvider:
    @staticmethod
    def get_installed_tool_version(tool_name: str) -> SemanticVersion:
        try:
            return SemanticVersion.from_string(version(tool_name))
        except PackageNotFoundError:
            raise InstalledToolNotFoundException(tool_name)


# TODO add timeouts and exception handling for requests
# TODO Alternatively use the gitpython package?
class GithubVersionProvider(VersionProvider):
    @staticmethod
    def get_latest_version(repo_name: str, tags: bool = False) -> SemanticVersion:
        if tags:
            tags_list = requests.get(f"https://api.github.com/repos/{repo_name}/tags").json()
            versions = [SemanticVersion.from_string(v["name"]) for v in tags_list]
            versions.sort(reverse=True)
            return versions[0]

        package_info = requests.get(
            f"https://api.github.com/repos/{repo_name}/releases/latest"
        ).json()
        return SemanticVersion.from_string(package_info["tag_name"])


class PyPiVersionProvider(VersionProvider):
    @staticmethod
    def get_latest_version(project_name: str) -> SemanticVersion:
        package_info = requests.get(f"https://pypi.org/pypi/{project_name}/json").json()
        released_versions = package_info["releases"].keys()
        parsed_released_versions = [SemanticVersion.from_string(v) for v in released_versions]
        parsed_released_versions.sort(reverse=True)
        return parsed_released_versions[0]


class DeprecatedVersionFileVersionProvider(VersionProvider):
    def __init__(self, file_provider: YamlFileProvider):
        self.file_provider = file_provider or YamlFileProvider

    def get_required_version(self) -> SemanticVersion:
        deprecated_version_file = Path(PLATFORM_HELPER_VERSION_FILE)
        try:
            loaded_version = self.file_provider.load(deprecated_version_file)
            version_from_file = SemanticVersion.from_string(loaded_version)
        except FileProviderException:
            version_from_file = None
        return version_from_file
