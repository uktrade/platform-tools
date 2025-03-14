from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import pytest

from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.version import AWSVersionProvider
from dbt_platform_helper.providers.version import CopilotVersionProvider
from dbt_platform_helper.providers.version import GithubVersionProvider
from dbt_platform_helper.providers.version import InstalledVersionProvider
from dbt_platform_helper.providers.version import InstalledVersionProviderException
from dbt_platform_helper.providers.version import PyPiVersionProvider


class MockGithubReleaseResponse:
    @staticmethod
    def json():
        return {"tag_name": "1.1.1"}


class MockGithubTagResponse:
    @staticmethod
    def json():
        return [{"name": "1.1.1"}, {"name": "1.2.3"}]


class MockPyPiResponse:
    @staticmethod
    def json():
        return {"releases": {"1.1.1": [], "1.2.3": [], "1.1.0": None}}


class TestInstalledVersionProvider:
    @patch("dbt_platform_helper.providers.version.version", return_value="1.1.1")
    def test_get_locally_installed_tool_version(self, mock_version):
        assert InstalledVersionProvider.get_installed_tool_version("test") == SemanticVersion(
            1, 1, 1
        )
        mock_version.assert_called_once_with("test")

    @patch("dbt_platform_helper.providers.version.version", return_value="")
    def test_get_locally_installed_tool_version_given_package_not_found_exception(
        self, mock_version
    ):
        mock_version.side_effect = PackageNotFoundError
        with pytest.raises(InstalledVersionProviderException) as exc:
            InstalledVersionProvider.get_installed_tool_version("test")

        assert "Package 'test' not found" in str(exc)


class TestGithubVersionProvider:
    @patch("requests.get", return_value=MockGithubReleaseResponse())
    def test_get_github_version_from_releases(self, request_get):
        assert GithubVersionProvider.get_latest_version("test/repo") == SemanticVersion(1, 1, 1)
        request_get.assert_called_once_with(
            "https://api.github.com/repos/test/repo/releases/latest"
        )

    @patch("requests.get", return_value=MockGithubTagResponse())
    def test_get_github_version_from_tags(self, request_get):
        assert GithubVersionProvider.get_latest_version("test/repo", True) == SemanticVersion(
            1, 2, 3
        )
        request_get.assert_called_once_with("https://api.github.com/repos/test/repo/tags")


class TestPyPiVersionProvider:
    @patch("requests.get", return_value=MockPyPiResponse())
    def test_get_latest_version(self, request_get):
        result = PyPiVersionProvider.get_latest_version("foo")
        assert result == SemanticVersion(1, 2, 3)
        request_get.assert_called_once_with(f"https://pypi.org/pypi/foo/json")


class TestAWSVersionProvider:
    @patch("subprocess.run")
    @patch(
        "dbt_platform_helper.providers.version.GithubVersionProvider.get_latest_version",
        return_value=SemanticVersion(2, 0, 0),
    )
    def test_get_aws_versions(self, mock_get_github_released_version, mock_run):
        mock_run.return_value.stdout = b"aws-cli/1.0.0"
        versions = AWSVersionProvider.get_versions()

        assert versions.installed == SemanticVersion(1, 0, 0)
        assert versions.latest == SemanticVersion(2, 0, 0)


class TestCopilotVersionProvider:
    @patch("subprocess.run")
    @patch(
        "dbt_platform_helper.providers.version.GithubVersionProvider.get_latest_version",
        return_value=SemanticVersion(2, 0, 0),
    )
    def test_copilot_versions(self, mock_get_github_released_version, mock_run):
        mock_run.return_value.stdout = b"1.0.0"

        versions = CopilotVersionProvider.get_versions()

        assert versions.installed == SemanticVersion(1, 0, 0)
        assert versions.latest == SemanticVersion(2, 0, 0)
