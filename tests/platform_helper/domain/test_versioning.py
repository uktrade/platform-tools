import os
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.domain.versioning import PlatformHelperVersionNotFoundException
from dbt_platform_helper.domain.versioning import skip_version_check
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.version import DeprecatedVersionFileVersionProvider
from dbt_platform_helper.providers.version import LocalVersionProvider
from dbt_platform_helper.providers.version import PyPiVersionProvider
from tests.platform_helper.conftest import (
    INVALID_PLATFORM_CONFIG_WITH_PLATFORM_VERSION_OVERRIDES,
)


@pytest.fixture
def mock_local_version_provider():
    mock_local_version_provider = Mock(spec=LocalVersionProvider)
    mock_local_version_provider.get_installed_tool_version.return_value = SemanticVersion(1, 0, 1)
    return mock_local_version_provider


@pytest.fixture
def mock_io_provider():
    return Mock(spec=ClickIOProvider)


@pytest.fixture
def mock_config_provider():
    return Mock(spec=ConfigProvider)


@pytest.fixture
def mock_version_file_version_provider():
    return Mock(spec=DeprecatedVersionFileVersionProvider)


@pytest.fixture
def mock_skip():
    skip = Mock()
    skip.return_value = False
    return skip


@pytest.fixture
def mock_pypi_provider():
    mock_pypi_provider = Mock(spec=PyPiVersionProvider)
    mock_pypi_provider.get_latest_version.return_value = SemanticVersion(2, 0, 0)
    return mock_pypi_provider


class TestPlatformHelperVersioningCheckPlatformHelperMismatch:
    def test_check_platform_helper_version_shows_warning_when_different_than_file_spec(
        self,
        mock_io_provider,
        mock_local_version_provider,
        mock_pypi_provider,
        mock_skip,
        mock_version_file_version_provider,
    ):
        mock_version_file_version_provider.get_required_version.return_value = SemanticVersion(
            1, 0, 0
        )

        PlatformHelperVersioning(
            io=mock_io_provider,
            local_version_provider=mock_local_version_provider,
            pypi_provider=mock_pypi_provider,
            skip_version_checks=mock_skip,
            version_file_version_provider=mock_version_file_version_provider,
        ).check_platform_helper_version_mismatch()

        mock_io_provider.warn.assert_called_with(
            f"WARNING: You are running platform-helper v1.0.1 against v1.0.0 specified for the project.",
        )

    def test_check_platform_helper_version_shows_no_warning_when_same_as_file_spec(
        self,
        mock_io_provider,
        mock_local_version_provider,
        mock_pypi_provider,
        mock_skip,
        mock_version_file_version_provider,
    ):
        mock_version_file_version_provider.get_required_version.return_value = SemanticVersion(
            1, 0, 0
        )

        PlatformHelperVersioning(
            io=mock_io_provider,
            local_version_provider=mock_local_version_provider,
            pypi_provider=mock_pypi_provider,
            skip_version_checks=mock_skip,
            version_file_version_provider=mock_version_file_version_provider,
        ).check_platform_helper_version_mismatch()

        mock_io_provider.warn.assert_not_called
        mock_io_provider.error.assert_not_called

    def test_check_platform_helper_version_does_not_fall_over_if_platform_helper_version_file_not_present(
        self,
        valid_platform_config,
        mock_io_provider,
        mock_local_version_provider,
        mock_pypi_provider,
        mock_config_provider,
        mock_version_file_version_provider,
        mock_skip,
    ):
        mock_version_file_version_provider.get_required_version.return_value = None
        mock_config_provider.load_unvalidated_config_file.return_value = valid_platform_config

        PlatformHelperVersioning(
            io=mock_io_provider,
            local_version_provider=mock_local_version_provider,
            pypi_provider=mock_pypi_provider,
            config_provider=mock_config_provider,
            skip_version_checks=mock_skip,
            version_file_version_provider=mock_version_file_version_provider,
        ).check_platform_helper_version_mismatch()

        mock_io_provider.warn.assert_called_with(
            f"WARNING: You are running platform-helper v1.0.1 against v10.2.0 specified for the project.",
        )


class TestPlatformHelperVersioningGetRequiredVersionWithInvalidConfig:
    DEFAULT_VERSION = "1.2.3"
    INVALID_CONFIG_WITH_DEFAULT_VERSION = {
        "default_versions": {"platform-helper": DEFAULT_VERSION},
        "a_bogus_field_that_invalidates_config": "boo",
    }

    def test_default_given_invalid_config(self, mock_pypi_provider, mock_config_provider):
        expected = self.DEFAULT_VERSION

        mock_config_provider.load_unvalidated_config_file.return_value = (
            self.INVALID_CONFIG_WITH_DEFAULT_VERSION
        )

        result = PlatformHelperVersioning(
            config_provider=mock_config_provider, pypi_provider=mock_pypi_provider
        ).get_required_version()

        assert result == expected

    def test_pipeline_override_given_invalid_config(self, mock_pypi_provider, mock_config_provider):
        pipeline_override_version = "1.1.1"
        platform_config = self.INVALID_CONFIG_WITH_DEFAULT_VERSION
        platform_config["environment_pipelines"] = {
            "main": {
                "versions": {"platform-helper": pipeline_override_version},
            }
        }
        mock_config_provider.load_unvalidated_config_file.return_value = platform_config

        result = PlatformHelperVersioning(
            config_provider=mock_config_provider, pypi_provider=mock_pypi_provider
        ).get_required_version("main")

        assert result == pipeline_override_version

    def test_get_required_version_errors_if_version_is_not_specified_in_config(
        self,
        mock_pypi_provider,
        mock_config_provider,
        mock_local_version_provider,
        mock_skip,
        mock_io_provider,
    ):
        mock_config_provider.load_unvalidated_config_file.return_value = {"application": "my-app"}

        expected_message = f"""Cannot get dbt-platform-helper version from '{PLATFORM_CONFIG_FILE}'.
Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n  platform-helper: 1.0.1\n"""

        with pytest.raises(PlatformHelperVersionNotFoundException):
            PlatformHelperVersioning(
                io=mock_io_provider,
                config_provider=mock_config_provider,
                pypi_provider=mock_pypi_provider,
                local_version_provider=mock_local_version_provider,
                skip_version_checks=mock_skip,
            ).get_required_version()

        mock_io_provider.process_messages.assert_called_with(
            {"warnings": [], "errors": [expected_message]}
        )


class TestPlatformHelperVersioningGetRequiredVersion:
    def __init__(self, mock_config_provider):
        self.default_version = "1.2.3"
        self.platform_config = {
            "application": "my-app",
            "default_versions": {"platform-helper": self.default_version},
            "environments": {"dev": None},
            "environment_pipelines": {
                "main": {
                    "versions": {"platform-helper": "1.1.1"},
                    "slack_channel": "abc",
                    "trigger_on_push": True,
                    "environments": {"dev": None},
                }
            },
        }
        mock_config_provider.load_unvalidated_config_file.return_value = self.platform_config

    @pytest.mark.parametrize(
        "platform_helper_version_file_version, platform_config_default_version, pipeline_override, expected_version",
        [
            (SemanticVersion(0, 0, 1), None, None, "0.0.1"),
            (SemanticVersion(0, 0, 1), "1.0.0", None, "1.0.0"),
            (None, "3.0.0", "4.0.0", "4.0.0"),
            (SemanticVersion(0, 0, 1), "4.0.0", "5.0.0", "5.0.0"),
        ],
    )
    def test_versions_precedence(
        self,
        mock_local_version_provider,
        mock_version_file_version_provider,
        mock_config_provider,
        mock_pypi_provider,
        platform_helper_version_file_version,
        platform_config_default_version,
        pipeline_override,
        expected_version,
    ):
        mock_version_file_version_provider.get_required_version.return_value = (
            platform_helper_version_file_version
        )

        if platform_config_default_version:
            self.platform_config["default_versions"] = {
                "platform-helper": platform_config_default_version
            }

        if pipeline_override:
            self.platform_config["environment_pipelines"]["main"]["versions"] = {
                "platform-helper": pipeline_override
            }

        result = PlatformHelperVersioning(
            version_file_version_provider=mock_version_file_version_provider,
            config_provider=mock_config_provider,
            pypi_provider=mock_pypi_provider,
            local_version_provider=mock_local_version_provider,
            skip_version_checks=Mock(return_value=False),
        ).get_required_version("main")

        assert result == expected_version

    def test_fall_back_on_default_if_pipeline_option_is_not_a_valid_pipeline(
        self,
        mock_pypi_provider,
        mock_version_file_version_provider,
        mock_config_provider,
        mock_local_version_provider,
    ):
        result = PlatformHelperVersioning(
            version_file_version_provider=mock_version_file_version_provider,
            config_provider=mock_config_provider,
            pypi_provider=mock_pypi_provider,
            local_version_provider=mock_local_version_provider,
            skip_version_checks=Mock(return_value=False),
        ).get_required_version("bogus_pipeline_not_in_config")

        assert result == self.default_version


@pytest.mark.parametrize(
    "version_in_phv_file, version_in_platform_config, expected_warnings",
    (
        (
            True,
            False,
            [
                f"Please delete '{PLATFORM_HELPER_VERSION_FILE}' as it is now deprecated.",
                f"Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n  platform-helper: 3.3.3\n",
            ],
        ),
        (
            False,
            True,
            None,
        ),
        (
            True,
            True,
            [f"Please delete '{PLATFORM_HELPER_VERSION_FILE}' as it is now deprecated."],
        ),
    ),
)
def test_platform_helper_version_deprecation_warnings(
    mock_local_version_provider,
    mock_pypi_provider,
    mock_io_provider,
    mock_version_file_version_provider,
    mock_config_provider,
    version_in_phv_file,
    version_in_platform_config,
    expected_warnings,
):
    mock_pypi_provider.get_latest_version.return_value = SemanticVersion(2, 3, 4)
    platform_config = {"application": "my-app"}
    if version_in_platform_config:
        platform_config["default_versions"] = {"platform-helper": "2.2.2"}

    mock_config_provider.load_unvalidated_config_file.return_value = platform_config

    if version_in_phv_file:
        mock_version_file_version_provider.get_required_version.return_value = SemanticVersion(
            3, 3, 3
        )
    else:
        mock_version_file_version_provider.get_required_version.return_value = None

    PlatformHelperVersioning(
        io=mock_io_provider,
        version_file_version_provider=mock_version_file_version_provider,
        pypi_provider=mock_pypi_provider,
        config_provider=mock_config_provider,
        local_version_provider=mock_local_version_provider,
    ).get_required_version()

    if expected_warnings:
        mock_io_provider.process_messages.assert_called_with(
            {"warnings": expected_warnings, "errors": []}
        )
    else:
        mock_io_provider.process_messages.assert_called_with({})


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
def test_skip_version_check(
    mock_running_as_installed_package, mock_env_var, mock_installed, expected
):
    mock_running_as_installed_package.return_value = mock_installed
    mock_env = {"PLATFORM_TOOLS_SKIP_VERSION_CHECK": mock_env_var} if mock_env_var else {}
    with patch.dict(os.environ, mock_env):
        assert skip_version_check() == expected


class TestPlatformHelperVersioningGetStatus:
    def test_get_platform_helper_version_status_given_config_and_deprecated_version_file(
        self,
        valid_platform_config,
        mock_pypi_provider,
        mock_local_version_provider,
        mock_version_file_version_provider,
        mock_config_provider,
    ):
        mock_local_version_provider.get_installed_tool_version.return_value = SemanticVersion(
            1, 1, 1
        )
        mock_pypi_provider.get_latest_version.return_value = SemanticVersion(2, 3, 4)

        mock_version_file_version_provider.get_required_version.return_value = SemanticVersion(
            5, 6, 7
        )
        mock_config_provider.load_unvalidated_config_file.return_value = valid_platform_config

        version_status = PlatformHelperVersioning(
            local_version_provider=mock_local_version_provider,
            pypi_provider=mock_pypi_provider,
            config_provider=mock_config_provider,
            version_file_version_provider=mock_version_file_version_provider,
        ).get_version_status()

        assert version_status.local == SemanticVersion(1, 1, 1)
        assert version_status.latest == SemanticVersion(2, 3, 4)
        assert version_status.deprecated_version_file == SemanticVersion(5, 6, 7)
        assert version_status.platform_config_default == SemanticVersion(10, 2, 0)
        assert version_status.pipeline_overrides == {"test": "main", "prod-main": "9.0.9"}

    # TODO: refactor this when `get_version_status` becomes a private method and test implicitly
    #  through the public methods
    def test_get_platform_helper_version_status_when_excluding_project_versions(
        self,
        valid_platform_config,
        mock_pypi_provider,
        mock_local_version_provider,
        mock_version_file_version_provider,
        mock_config_provider,
    ):
        mock_local_version_provider.get_installed_tool_version.return_value = SemanticVersion(
            1, 1, 1
        )
        mock_pypi_provider.get_latest_version.return_value = SemanticVersion(2, 3, 4)

        version_status = PlatformHelperVersioning(
            local_version_provider=mock_local_version_provider,
            pypi_provider=mock_pypi_provider,
            config_provider=mock_config_provider,
            version_file_version_provider=mock_version_file_version_provider,
        ).get_version_status(include_project_versions=False)

        assert version_status.local == SemanticVersion(1, 1, 1)
        assert version_status.latest == SemanticVersion(2, 3, 4)
        assert version_status.deprecated_version_file is None
        assert version_status.platform_config_default is None
        assert version_status.pipeline_overrides == {}

    def test_get_platform_helper_version_status_with_invalid_yaml_in_platform_config(
        self,
        mock_pypi_provider,
        mock_local_version_provider,
        mock_version_file_version_provider,
        mock_config_provider,
    ):
        mock_local_version_provider.get_installed_tool_version.return_value = SemanticVersion(
            1, 1, 1
        )

        mock_pypi_provider.get_latest_version.return_value = SemanticVersion(2, 3, 4)
        mock_version_file_version_provider.get_required_version.return_value = SemanticVersion(
            5, 6, 7
        )
        mock_config_provider.load_unvalidated_config_file.return_value = {}

        version_status = PlatformHelperVersioning(
            local_version_provider=mock_local_version_provider,
            pypi_provider=mock_pypi_provider,
            config_provider=mock_config_provider,
            version_file_version_provider=mock_version_file_version_provider,
        ).get_version_status()

        assert version_status.local == SemanticVersion(1, 1, 1)
        assert version_status.latest == SemanticVersion(2, 3, 4)
        assert version_status.deprecated_version_file == SemanticVersion(5, 6, 7)
        assert version_status.platform_config_default == None
        assert version_status.pipeline_overrides == {}

    def test_get_platform_helper_version_status_with_invalid_config(
        self,
        mock_pypi_provider,
        mock_local_version_provider,
        mock_version_file_version_provider,
        mock_config_provider,
    ):
        mock_local_version_provider.get_installed_tool_version.return_value = SemanticVersion(
            1, 1, 1
        )

        invalid_platform_config = INVALID_PLATFORM_CONFIG_WITH_PLATFORM_VERSION_OVERRIDES
        mock_config_provider.load_unvalidated_config_file.return_value = yaml.safe_load(
            invalid_platform_config
        )

        mock_pypi_provider.get_latest_version.return_value = SemanticVersion(2, 3, 4)
        mock_version_file_version_provider.get_required_version.return_value = SemanticVersion(
            5, 6, 7
        )

        version_status = PlatformHelperVersioning(
            local_version_provider=mock_local_version_provider,
            pypi_provider=mock_pypi_provider,
            config_provider=mock_config_provider,
            version_file_version_provider=mock_version_file_version_provider,
        ).get_version_status()

        assert version_status.local == SemanticVersion(1, 1, 1)
        assert version_status.latest == SemanticVersion(2, 3, 4)
        assert version_status.deprecated_version_file == SemanticVersion(5, 6, 7)
        assert version_status.platform_config_default == SemanticVersion(1, 2, 3)
        assert version_status.pipeline_overrides == {"prod-main": "9.0.9"}


class TestPlatformHelperVersioningCheckIfNeedsUpdate:
    def test_check_platform_helper_version_needs_major_update_returns_red_warning_to_upgrade(
        self,
        no_skipping_version_checks,
        mock_local_version_provider,
        mock_pypi_provider,
        mock_io_provider,
    ):
        mock_local_version_provider.get_installed_tool_version.return_value = SemanticVersion(
            1, 0, 0
        )
        mock_pypi_provider.get_latest_version.return_value = SemanticVersion(2, 0, 0)

        PlatformHelperVersioning(
            io=mock_io_provider,
            pypi_provider=mock_pypi_provider,
            local_version_provider=mock_local_version_provider,
        ).check_if_needs_update()

        mock_io_provider.error.assert_called_with(
            "You are running platform-helper v1.0.0, upgrade to v2.0.0 by running run `pip install "
            "--upgrade dbt-platform-helper`."
        )

    def test_check_platform_helper_version_needs_minor_update_returns_warning_to_upgrade(
        self,
        no_skipping_version_checks,
        mock_local_version_provider,
        mock_pypi_provider,
        mock_io_provider,
    ):
        mock_local_version_provider.get_installed_tool_version.return_value = SemanticVersion(
            1, 0, 0
        )
        mock_pypi_provider.get_latest_version.return_value = SemanticVersion(1, 1, 0)

        PlatformHelperVersioning(
            io=mock_io_provider,
            pypi_provider=mock_pypi_provider,
            local_version_provider=mock_local_version_provider,
        ).check_if_needs_update()

        mock_io_provider.warn.assert_called_with(
            "You are running platform-helper v1.0.0, upgrade to v1.1.0 by running run `pip install "
            "--upgrade dbt-platform-helper`."
        )

    def test_no_version_warnings_or_errors_given_skip_version_checks(
        self, mock_skip, mock_io_provider, mock_local_version_provider, mock_pypi_provider
    ):
        mock_skip.return_value = True

        PlatformHelperVersioning(
            io=mock_io_provider,
            local_version_provider=mock_local_version_provider,
            pypi_provider=mock_pypi_provider,
            skip_version_checks=mock_skip,
        ).check_if_needs_update()

        mock_local_version_provider.get_installed_tool_version.assert_not_called()
        mock_io_provider.warn.assert_not_called()
        mock_io_provider.error.assert_not_called()
