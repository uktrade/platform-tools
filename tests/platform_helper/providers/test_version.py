from unittest.mock import patch
from importlib.metadata import PackageNotFoundError

import pytest

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.version import GithubVersionProvider, LocalVersionProvider, LocalVersionProviderException
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
        return {"releases": {"1.1.1": [], "1.2.3": []}}


class TestLocalVersionProvider:
    @patch("dbt_platform_helper.providers.version.version", return_value="1.1.1")
    def test_get_locally_installed_tool_version(self, mock_version):
        assert LocalVersionProvider.get_installed_tool_version("test") == SemanticVersion(1, 1, 1)
        mock_version.assert_called_once_with(
            "test"
        )
    
    @patch("dbt_platform_helper.providers.version.version", return_value="")
    def test_get_locally_installed_tool_version_given_package_not_found_exception(self, mock_version):
        mock_version.side_effect = PackageNotFoundError
        with pytest.raises(LocalVersionProviderException) as exc:
            LocalVersionProvider.get_installed_tool_version("test")
        
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
