from importlib.metadata import PackageNotFoundError
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.providers.version import AWSCLIInstalledVersionProvider
from dbt_platform_helper.providers.version import CopilotInstalledVersionProvider
from dbt_platform_helper.providers.version import GithubLatestVersionProvider
from dbt_platform_helper.providers.version import InstalledVersionProvider
from dbt_platform_helper.providers.version import InstalledVersionProviderException
from dbt_platform_helper.providers.version import PyPiLatestVersionProvider


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
    def test_get_semantic_version(self, mock_version):
        assert InstalledVersionProvider.get_semantic_version("test") == SemanticVersion(1, 1, 1)
        mock_version.assert_called_once_with("test")

    @patch("dbt_platform_helper.providers.version.version", return_value="")
    def test_get_semantic_version_given_package_not_found_exception(self, mock_version):
        mock_version.side_effect = PackageNotFoundError
        with pytest.raises(InstalledVersionProviderException) as exc:
            InstalledVersionProvider.get_semantic_version("test")

        assert "Package 'test' not found" in str(exc)


class TestGithubLatestVersionProvider:
    def test_get_semantic_version_from_releases(self):
        requests_mock = MagicMock()
        requests_mock.get.return_value = MockGithubReleaseResponse()
        assert GithubLatestVersionProvider.get_semantic_version(
            "test/repo", request_session=requests_mock
        ) == SemanticVersion(1, 1, 1)
        requests_mock.get.assert_called_once_with(
            "https://api.github.com/repos/test/repo/releases/latest"
        )

    def test_get_semantic_version_from_tags(self):
        requests_mock = MagicMock()
        requests_mock.get.return_value = MockGithubTagResponse()
        assert GithubLatestVersionProvider.get_semantic_version(
            "test/repo", True, request_session=requests_mock
        ) == SemanticVersion(1, 2, 3)
        requests_mock.get.assert_called_once_with("https://api.github.com/repos/test/repo/tags")

    def test_get_semantic_version_returns_none_on_error(self):
        mock_io = MagicMock()
        requests_mock = MagicMock()
        requests_mock.get.side_effect = Exception("doesnt-matter")
        assert (
            GithubLatestVersionProvider.get_semantic_version(
                "test/repo", request_session=requests_mock, io=mock_io
            )
            is None
        )
        mock_io.error.assert_called_with(
            "Exception occured when calling Github with:\ndoesnt-matter"
        )
        requests_mock.get.assert_called_once_with(
            "https://api.github.com/repos/test/repo/releases/latest"
        )


class TestPyPiLatestVersionProvider:
    def test_get_semantic_version(self):
        requests_mock = MagicMock()
        requests_mock.get.return_value = MockPyPiResponse()
        result = PyPiLatestVersionProvider.get_semantic_version(
            "foo", request_session=requests_mock
        )
        assert result == SemanticVersion(1, 2, 3)
        requests_mock.get.assert_called_once_with(f"https://pypi.org/pypi/foo/json")

    def test_get_semantic_version_returns_none_on_error(self):
        mock_io = MagicMock()
        requests_mock = MagicMock()
        requests_mock.get.side_effect = Exception("doesnt-matter")
        assert (
            PyPiLatestVersionProvider.get_semantic_version(
                "foo", request_session=requests_mock, io=mock_io
            )
            is None
        )
        mock_io.error.assert_called_with("Exception occured when calling PyPi with:\ndoesnt-matter")
        requests_mock.get.assert_called_once_with(f"https://pypi.org/pypi/foo/json")


@pytest.mark.parametrize(
    "mock_run_stdout, expected",
    (
        (b"aws-cli/1.0.0", SemanticVersion(1, 0, 0)),
        (b"aws-cli/1.0.1", SemanticVersion(1, 0, 1)),
        (b"aws-cli/1.1.1", SemanticVersion(1, 1, 1)),
        (b"aws-cli/2.0.0", SemanticVersion(2, 0, 0)),
        (b"command not found: copilot", None),
    ),
)
class TestAWSCLIInstalledVersionProvider:
    @patch("subprocess.run")
    def test_get_semantic_version(self, mock_run, mock_run_stdout, expected):
        mock_run.return_value.stdout = mock_run_stdout

        result = AWSCLIInstalledVersionProvider.get_semantic_version()

        assert result == expected


class TestCopilotVersioning:
    @pytest.mark.parametrize(
        "mock_run_stdout, expected",
        (
            (b"1.0.0", SemanticVersion(1, 0, 0)),
            (b"1.0.1", SemanticVersion(1, 0, 1)),
            (b"1.1.1", SemanticVersion(1, 1, 1)),
            (b"2.0.0", SemanticVersion(2, 0, 0)),
            (b"command not found: copilot", None),
        ),
    )
    @patch("subprocess.run")
    def test_get_semantic_version(self, mock_run, mock_run_stdout, expected):
        mock_run.return_value.stdout = mock_run_stdout

        result = CopilotInstalledVersionProvider().get_semantic_version()

        assert result == expected
