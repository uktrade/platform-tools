from abc import ABC

import requests

from dbt_platform_helper.providers.semantic_version import SemanticVersion


class VersionProvider(ABC):
    pass


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
