import os
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_OVERRIDE_KEY
from dbt_platform_helper.constants import (
    TERRAFORM_CODEBASE_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR,
)
from dbt_platform_helper.constants import (
    TERRAFORM_ENVIRONMENT_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR,
)
from dbt_platform_helper.domain.versioning import ENVIRONMENT_PIPELINE_MODULE_PATH
from dbt_platform_helper.domain.versioning import AWSVersioning
from dbt_platform_helper.domain.versioning import CopilotVersioning
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.domain.versioning import skip_version_checks
from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.version import InstalledVersionProvider
from dbt_platform_helper.providers.version import PyPiLatestVersionProvider
from dbt_platform_helper.providers.version import VersionProvider


class PlatformHelperVersioningMocks:
    def __init__(self, **kwargs):
        self.mock_io = kwargs.get("io", Mock(spec=ClickIOProvider))
        self.mock_config_provider = kwargs.get("config_provider", Mock(spec=ConfigProvider))
        self.mock_config_provider.load_and_validate_platform_config.return_value = {}
        self.mock_platform_helper_version_override = "platform_helper_param_override"
        self.mock_latest_version_provider = kwargs.get(
            "latest_version_provider", Mock(spec=PyPiLatestVersionProvider)
        )
        self.mock_installed_version_provider = kwargs.get(
            "installed_version_provider", Mock(spec=InstalledVersionProvider)
        )
        self.mock_skip_versioning_checks = kwargs.get("skip_versioning_checks", False)
        self.mock_environment_variable_provider = {
            TERRAFORM_ENVIRONMENT_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR: "env_override",
            TERRAFORM_CODEBASE_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR: "codebase_env_override",
            PLATFORM_HELPER_VERSION_OVERRIDE_KEY: "platform_helper_env_override",
        }

    def params(self):
        return {
            "io": self.mock_io,
            "config_provider": self.mock_config_provider,
            "latest_version_provider": self.mock_latest_version_provider,
            "installed_version_provider": self.mock_installed_version_provider,
            "skip_versioning_checks": self.mock_skip_versioning_checks,
            "platform_helper_version_override": self.mock_platform_helper_version_override,
            "environment_variable_provider": self.mock_environment_variable_provider,
        }


@pytest.fixture
def mocks():
    platform_config = {"default_versions": {"platform-helper": "1.0.0"}}

    mocks = PlatformHelperVersioningMocks()
    mocks.mock_config_provider.load_and_validate_platform_config.return_value = platform_config
    mocks.mock_config_provider.load_unvalidated_config_file.return_value = platform_config
    return mocks


# TODO
# generate commands should error when run locally - "Your service is running on a managed platform.  Changes must be made by running the pipelines"
# generate commands must not error when run in the pipeline
# other commands - error if not on latest version?
# Are we allowing platform downgrades or are we explicitly not allowing them?
class TestPlatformHelperVersioningCheckPlatformHelperMismatch:

    def test_is_managed(self, mocks):
        platform_config = {"default_versions": {"platform-helper": "auto"}}
        mocks.mock_config_provider.load_and_validate_platform_config.return_value = platform_config
        mocks.mock_config_provider.load_unvalidated_config_file.return_value = platform_config

        result = PlatformHelperVersioning(**mocks.params()).is_managed()

        assert result == True

    def test_not_is_managed(self, mocks):
        result = PlatformHelperVersioning(**mocks.params()).is_managed()

        assert result == False

    def test_shows_warning_when_different_than_file_spec(self, mocks):
        mocks.mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(
            1, 0, 1
        )

        PlatformHelperVersioning(**mocks.params()).check_platform_helper_version_mismatch()

        mocks.mock_io.warn.assert_called_with(
            f"WARNING: You are running platform-helper v1.0.1 against v1.0.0 specified for the project.",
        )

    def test_shows_no_warning_when_same_as_file_spec(self, mocks):
        mocks.mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(
            1, 0, 0
        )

        PlatformHelperVersioning(**mocks.params()).check_platform_helper_version_mismatch()

        mocks.mock_io.warn.assert_not_called
        mocks.mock_io.error.assert_not_called


class TestPlatformHelperVersioningGetRequiredVersion:
    def test_platform_helper_get_required_version(self, mocks):
        result = PlatformHelperVersioning(**mocks.params()).get_required_version()

        assert str(result) == "1.0.0"
        mocks.mock_config_provider.load_unvalidated_config_file.assert_called_once()
        mocks.mock_config_provider.load_and_validate_platform_config.assert_not_called()


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
    def test_if_platform_helper_version_needs_major_update_returns_error_with_red_message_to_upgrade(
        self,
        mocks,
    ):
        mocks.mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(
            1, 0, 0
        )
        mocks.mock_latest_version_provider.get_semantic_version.return_value = SemanticVersion(
            2, 0, 0
        )

        PlatformHelperVersioning(**mocks.params()).check_if_needs_update()

        mocks.mock_io.error.assert_called_with(
            "You are running platform-helper v1.0.0, upgrade to v2.0.0 by running run `pip install "
            "--upgrade dbt-platform-helper`."
        )

    # TODO Not sure we want this behaviour.  It prevents downgrades which we may need to do.
    # It also forces upgrades when perhaps not necessary.
    # def test_old_platform_helper_version_with_managed_versioning_returns_error_with_red_message_to_upgrade(
    #     self,
    #     mocks,
    # ):
    #     mocks.installed_version_provider.get_semantic_version.return_value = SemanticVersion(
    #         2, 0, 0
    #     )
    #     mocks.latest_version_provider.get_semantic_version.return_value = SemanticVersion(2, 1, 0)

    #     PlatformHelperVersioning(**mocks.params()).check_if_needs_update()

    #     mocks.io.error.assert_called_with(
    #         "Your service is on the managed platform and commands must be run with latest platform-helper version."
    #         "You are running platform-helper v2.0.0. Upgrade to v2.1.0 by running `pip install "
    #         "--upgrade dbt-platform-helper`."
    #     )

    def test_if_platform_helper_version_needs_minor_update_returns_warning_to_upgrade(
        self,
        mocks,
    ):
        mocks.mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(
            1, 0, 0
        )
        mocks.mock_latest_version_provider.get_semantic_version.return_value = SemanticVersion(
            1, 1, 0
        )

        PlatformHelperVersioning(**mocks.params()).check_if_needs_update()

        mocks.mock_io.warn.assert_called_with(
            "You are running platform-helper v1.0.0, upgrade to v1.1.0 by running run `pip install "
            "--upgrade dbt-platform-helper`."
        )

    def test_no_version_warnings_or_errors_given_skip_version_checks(self, mocks):
        mocks.mock_skip_versioning_checks = True

        PlatformHelperVersioning(**mocks.params()).check_if_needs_update()

        mocks.mock_installed_version_provider.get_semantic_version.assert_not_called()
        mocks.mock_io.warn.assert_not_called()
        mocks.mock_io.error.assert_not_called()


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


class TestPlatformHelperVersioningPipelinesVersioning:

    def test_environment_platform_helper_versioning_precedence_with_env_override(self):
        mocks = PlatformHelperVersioningMocks()
        result = PlatformHelperVersioning(
            **mocks.params()
        ).get_environment_pipeline_modules_version()
        assert result == "env_override"

    def test_environment_platform_helper_versioning_without_env_override_falls_back_to_param_override(
        self,
    ):
        mocks = PlatformHelperVersioningMocks()
        mocks.mock_environment_variable_provider[
            TERRAFORM_ENVIRONMENT_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR
        ] = None
        result = PlatformHelperVersioning(
            **mocks.params()
        ).get_environment_pipeline_modules_version()
        assert result == f"{ENVIRONMENT_PIPELINE_MODULE_PATH}platform_helper_param_override"

    def test_environment_platform_helper_versioning_without_param_override_falls_back_to_env_override(
        self,
    ):
        mocks = PlatformHelperVersioningMocks()
        mocks.mock_environment_variable_provider[
            TERRAFORM_ENVIRONMENT_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR
        ] = None
        mocks.mock_platform_helper_version_override = None
        result = PlatformHelperVersioning(
            **mocks.params()
        ).get_environment_pipeline_modules_version()
        assert result == f"{ENVIRONMENT_PIPELINE_MODULE_PATH}platform_helper_env_override"

    def test_environment_platform_helper_versioning_without_any_override_defaults_to_config(
        self, platform_config_for_env_pipelines
    ):
        platform_config_for_env_pipelines["default_versions"] = {"platform-helper": "1.1.1"}

        mocks = PlatformHelperVersioningMocks()
        mocks.mock_config_provider.load_and_validate_platform_config.return_value = (
            platform_config_for_env_pipelines
        )
        mocks.mock_environment_variable_provider[
            TERRAFORM_ENVIRONMENT_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR
        ] = None
        mocks.mock_environment_variable_provider[PLATFORM_HELPER_VERSION_OVERRIDE_KEY] = None
        mocks.mock_platform_helper_version_override = None
        result = PlatformHelperVersioning(
            **mocks.params()
        ).get_environment_pipeline_modules_version()
        assert result == f"{ENVIRONMENT_PIPELINE_MODULE_PATH}1.1.1"


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
