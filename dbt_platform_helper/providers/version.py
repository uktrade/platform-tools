import re
import subprocess
from abc import ABC
from abc import abstractmethod
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
from typing import Union

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider


def set_up_retry():
    session = Session()
    retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[403, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


class InstalledVersionProviderException(PlatformException):
    pass


class InstalledToolNotFoundException(InstalledVersionProviderException):
    def __init__(
        self,
        tool_name: str,
    ):
        super().__init__(f"Package '{tool_name}' not found.")


class VersionProvider(ABC):
    @abstractmethod
    def get_semantic_version() -> SemanticVersion:
        raise NotImplementedError("Must be implemented in subclasses")


class InstalledVersionProvider:
    @staticmethod
    def get_semantic_version(tool_name: str) -> SemanticVersion:
        try:
            return SemanticVersion.from_string(version(tool_name))

        except PackageNotFoundError:
            raise InstalledToolNotFoundException(tool_name)


class GithubLatestVersionProvider(VersionProvider):
    @staticmethod
    def get_semantic_version(
        repo_name: str, tags: bool = False, request_session=set_up_retry(), io=ClickIOProvider()
    ) -> Union[SemanticVersion, None]:

        semantic_version = None
        try:
            if tags:
                response = request_session.get(f"https://api.github.com/repos/{repo_name}/tags")

                versions = [SemanticVersion.from_string(v["name"]) for v in response.json()]
                versions.sort(reverse=True)
                semantic_version = versions[0]
            else:
                package_info = request_session.get(
                    f"https://api.github.com/repos/{repo_name}/releases/latest"
                ).json()
                semantic_version = SemanticVersion.from_string(package_info["tag_name"])
        except Exception as e:
            io.error(f"Exception occured when calling Github with:\n{str(e)}")

        return semantic_version


class PyPiLatestVersionProvider(VersionProvider):
    @staticmethod
    def get_semantic_version(
        project_name: str, request_session=set_up_retry(), io=ClickIOProvider()
    ) -> Union[SemanticVersion, None]:
        semantic_version = None
        try:
            package_info = request_session.get(f"https://pypi.org/pypi/{project_name}/json").json()
            released_versions = package_info["releases"].keys()
            parsed_released_versions = [SemanticVersion.from_string(v) for v in released_versions]
            parsed_released_versions.sort(reverse=True)
            semantic_version = parsed_released_versions[0]
        except Exception as e:
            io.error(f"Exception occured when calling PyPi with:\n{str(e)}")
        return semantic_version


class AWSCLIInstalledVersionProvider(VersionProvider):
    @staticmethod
    def get_semantic_version() -> Union[SemanticVersion, None]:
        installed_aws_version = None
        try:
            response = subprocess.run("aws --version", capture_output=True, shell=True)
            matched = re.match(r"aws-cli/([0-9.]+)", response.stdout.decode("utf8"))
            installed_aws_version = matched.group(1)
        except (ValueError, AttributeError):
            pass
        return SemanticVersion.from_string(installed_aws_version)


class CopilotInstalledVersionProvider(VersionProvider):
    @staticmethod
    def get_semantic_version() -> Union[SemanticVersion, None]:
        copilot_version = None

        try:
            response = subprocess.run("copilot --version", capture_output=True, shell=True)
            [copilot_version] = re.findall(r"[0-9.]+", response.stdout.decode("utf8"))
        except ValueError:
            pass

        return SemanticVersion.from_string(copilot_version)
