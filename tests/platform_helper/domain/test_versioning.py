import os
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from dbt_platform_helper.domain.versioning import AWSVersioning
from dbt_platform_helper.domain.versioning import CopilotVersioning
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.domain.versioning import skip_version_checks
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.version import InstalledVersionProvider
from dbt_platform_helper.providers.version import PyPiLatestVersionProvider
from dbt_platform_helper.providers.version import VersionProvider


class PlatformHelperVersioningMocks:
    def __init__(self, **kwargs):
        self.io = kwargs.get("io", Mock(spec=ClickIOProvider))
        self.config_provider = kwargs.get("config_provider", Mock(spec=ConfigProvider))
        self.config_provider.load_and_validate_platform_config.return_value = {}
        self.latest_version_provider = kwargs.get(
            "latest_version_provider", Mock(spec=PyPiLatestVersionProvider)
        )
        self.installed_version_provider = kwargs.get(
            "installed_version_provider", Mock(spec=InstalledVersionProvider)
        )
        self.skip_versioning_checks = kwargs.get("skip_versioning_checks", False)

    def params(self):
        return {
            "io": self.io,
            "config_provider": self.config_provider,
            "latest_version_provider": self.latest_version_provider,
            "installed_version_provider": self.installed_version_provider,
            "skip_versioning_checks": self.skip_versioning_checks,
        }


@pytest.fixture
def mocks():
    platform_config = {"default_versions": {"platform-helper": "1.0.0"}}

    mocks = PlatformHelperVersioningMocks()
    mocks.config_provider.load_and_validate_platform_config.return_value = platform_config
    mocks.config_provider.load_unvalidated_config_file.return_value = platform_config
    return mocks


class TestPlatformHelperVersioningCheckPlatformHelperMismatch:
    def test_shows_warning_when_different_than_file_spec(self, mocks):
        mocks.installed_version_provider.get_semantic_version.return_value = SemanticVersion(
            1, 0, 1
        )

        PlatformHelperVersioning(**mocks.params()).check_platform_helper_version_mismatch()

        mocks.io.warn.assert_called_with(
            f"WARNING: You are running platform-helper v1.0.1 against v1.0.0 specified for the project.",
        )

    def test_shows_no_warning_when_same_as_file_spec(self, mocks):
        mocks.installed_version_provider.get_semantic_version.return_value = SemanticVersion(
            1, 0, 0
        )

        PlatformHelperVersioning(**mocks.params()).check_platform_helper_version_mismatch()

        mocks.io.warn.assert_not_called
        mocks.io.error.assert_not_called


class TestPlatformHelperVersioningGetRequiredVersion:
    def test_platform_helper_get_required_version(self, mocks):
        result = PlatformHelperVersioning(**mocks.params()).get_required_version()

        assert str(result) == "1.0.0"
        mocks.config_provider.load_unvalidated_config_file.assert_called_once()
        mocks.config_provider.load_and_validate_platform_config.assert_not_called()


@pytest.mark.parametrize(
    "mock_env_var, mock_installed, expected",
    (
        (
            "set",
            True,
            True,
        ),
        (
            "set",
            False,
            True,
        ),
        (
            None,
            True,
            False,
        ),
        (
            None,
            False,
            True,
        ),
    ),
)
@patch(
    "dbt_platform_helper.domain.versioning.running_as_installed_package",
)
def test_skip_version_checks(
    mock_running_as_installed_package, mock_env_var, mock_installed, expected
):
    mock_running_as_installed_package.return_value = mock_installed
    mock_env = {"PLATFORM_TOOLS_SKIP_VERSION_CHECK": mock_env_var} if mock_env_var else {}
    with patch.dict(os.environ, mock_env):
        assert skip_version_checks() == expected


class TestPlatformHelperVersioningCheckIfNeedsUpdate:
    def test_if_platform_helper_version_needs_major_update_returns_red_warning_to_upgrade(
        self,
        mocks,
    ):
        mocks.installed_version_provider.get_semantic_version.return_value = SemanticVersion(
            1, 0, 0
        )
        mocks.latest_version_provider.get_semantic_version.return_value = SemanticVersion(2, 0, 0)

        PlatformHelperVersioning(**mocks.params()).check_if_needs_update()

        mocks.io.error.assert_called_with(
            "You are running platform-helper v1.0.0, upgrade to v2.0.0 by running run `pip install "
            "--upgrade dbt-platform-helper`."
        )

    def test_if_platform_helper_version_needs_minor_update_returns_warning_to_upgrade(
        self,
        mocks,
    ):
        mocks.installed_version_provider.get_semantic_version.return_value = SemanticVersion(
            1, 0, 0
        )
        mocks.latest_version_provider.get_semantic_version.return_value = SemanticVersion(1, 1, 0)

        PlatformHelperVersioning(**mocks.params()).check_if_needs_update()

        mocks.io.warn.assert_called_with(
            "You are running platform-helper v1.0.0, upgrade to v1.1.0 by running run `pip install "
            "--upgrade dbt-platform-helper`."
        )

    def test_no_version_warnings_or_errors_given_skip_version_checks(self, mocks):
        mocks.skip_versioning_checks = True

        PlatformHelperVersioning(**mocks.params()).check_if_needs_update()

        mocks.installed_version_provider.get_semantic_version.assert_not_called()
        mocks.io.warn.assert_not_called()
        mocks.io.error.assert_not_called()


class VersioningMocks:
    def __init__(self, **kwargs):
        self.latest_version_provider = kwargs.get(
            "latest_version_provider", Mock(spec=VersionProvider)
        )
        self.installed_version_provider = kwargs.get(
            "installed_version_provider", Mock(spec=VersionProvider)
        )

    def params(self):
        return {
            "latest_version_provider": self.latest_version_provider,
            "installed_version_provider": self.installed_version_provider,
        }


class TestAWSVersioning:
    def test_get_aws_versioning(self):
        mocks = VersioningMocks()
        mocks.installed_version_provider.get_semantic_version.return_value = SemanticVersion(
            1, 0, 0
        )
        mocks.latest_version_provider.get_semantic_version.return_value = SemanticVersion(2, 0, 0)

        result = AWSVersioning(**mocks.params()).get_version_status()

        assert result.installed == SemanticVersion(1, 0, 0)
        assert result.latest == SemanticVersion(2, 0, 0)


class TestCopilotVersioning:
    def test_copilot_versioning(self):
        mocks = VersioningMocks()
        mocks.installed_version_provider.get_semantic_version.return_value = SemanticVersion(
            1, 0, 0
        )
        mocks.latest_version_provider.get_semantic_version.return_value = SemanticVersion(2, 0, 0)

        result = CopilotVersioning(**mocks.params()).get_version_status()

        assert result.installed == SemanticVersion(1, 0, 0)
        assert result.latest == SemanticVersion(2, 0, 0)
