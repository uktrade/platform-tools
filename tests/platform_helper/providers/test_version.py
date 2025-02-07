from unittest.mock import patch

from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.version import GithubVersionProvider
from dbt_platform_helper.providers.version import PyPiVersionProvider


class MockGithubReleaseResponse:
    @staticmethod
    def json():
        return {"tag_name": "1.1.1"}


class MockGithubTagResponse:
    @staticmethod
    def json():
        return [{"name": "1.1.1"}, {"name": "1.2.3"}]


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
    @patch("requests.get", return_value=MockGithubReleaseResponse())
    def test_get_latest_version(self, request_get):
        result = PyPiVersionProvider.get_latest_version("foo")
        assert result == SemanticVersion(1, 1, 1)
        # request_get.assert_called_once_with("https://api.github.com/repos/test/repo/releases/latest")
