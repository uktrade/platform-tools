import os
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.domain.versioning import PlatformHelperVersionNotFoundException
from dbt_platform_helper.domain.versioning import skip_version_check
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.version import LocalVersionProvider
from dbt_platform_helper.providers.version import PyPiVersionProvider


@pytest.fixture
def mock_local_version_provider():
    mock_local_version_provider = Mock(spec=LocalVersionProvider)
    mock_local_version_provider.get_installed_tool_version.return_value = SemanticVersion(1, 0, 1)
    return mock_local_version_provider


@pytest.fixture
def mock_io_provider():
    return Mock(spec=ClickIOProvider)


@pytest.fixture
def mock_skip():
    return Mock()


@pytest.fixture
def mock_pypi_provider():
    mock_pypi_provider = Mock(spec=PyPiVersionProvider)
    mock_pypi_provider.get_latest_version.return_value = SemanticVersion(2, 0, 0)
    return mock_pypi_provider


def test_check_platform_helper_version_shows_warning_when_different_than_file_spec(
    no_skipping_version_checks,
    mock_io_provider,
    mock_local_version_provider,
    mock_pypi_provider,
    fakefs,
):
    fakefs.create_file(PLATFORM_HELPER_VERSION_FILE, contents="1.0.0")
    required_version = PlatformHelperVersioning(
        io=mock_io_provider,
        local_version_provider=mock_local_version_provider,
        pypi_provider=mock_pypi_provider,
    )

    required_version.check_platform_helper_version_mismatch()

    mock_io_provider.warn.assert_called_with(
        f"WARNING: You are running platform-helper v1.0.1 against v1.0.0 specified for the project.",
    )


def test_check_platform_helper_version_shows_no_warning_when_same_as_file_spec(
    no_skipping_version_checks,
    mock_io_provider,
    mock_local_version_provider,
    mock_pypi_provider,
    fakefs,
):
    fakefs.create_file(PLATFORM_HELPER_VERSION_FILE, contents="1.0.0")

    required_version = PlatformHelperVersioning(
        io=mock_io_provider,
        local_version_provider=mock_local_version_provider,
        pypi_provider=mock_pypi_provider,
    )

    required_version.check_platform_helper_version_mismatch()

    mock_io_provider.warn.assert_not_called
    mock_io_provider.error.assert_not_called


def test_check_platform_helper_version_does_not_fall_over_if_platform_helper_version_file_not_present(
    no_skipping_version_checks,
    mock_io_provider,
    mock_local_version_provider,
    mock_pypi_provider,
    fakefs,
    valid_platform_config,
):
    config = valid_platform_config
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(config))

    required_version = PlatformHelperVersioning(
        io=mock_io_provider,
        local_version_provider=mock_local_version_provider,
        pypi_provider=mock_pypi_provider,
    )

    required_version.check_platform_helper_version_mismatch()

    mock_io_provider.warn.assert_called_with(
        f"WARNING: You are running platform-helper v1.0.1 against v10.2.0 specified for the project.",
    )


@patch(
    "dbt_platform_helper.providers.version.PyPiVersionProvider.get_latest_version",
    return_value="10.9.9",
)
class TestVersionCommandWithInvalidConfig:
    DEFAULT_VERSION = "1.2.3"
    INVALID_CONFIG = {
        "default_versions": {"platform-helper": DEFAULT_VERSION},
        "a_bogus_field_that_invalidates_config": "foo",
    }

    def test_works_given_invalid_config(self, mock_latest_release, fakefs):
        default_version = "1.2.3"
        platform_config = self.INVALID_CONFIG
        fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(platform_config))

        result = PlatformHelperVersioning()._resolve_required_version(
            "bogus_pipeline", version_status=PlatformHelperVersioning().get_version_status()
        )

        assert result == default_version

    def test_pipeline_override_given_invalid_config(self, mock_latest_release, fakefs):
        pipeline_override_version = "1.1.1"
        platform_config = self.INVALID_CONFIG
        platform_config["environment_pipelines"] = {
            "main": {
                "versions": {"platform-helper": pipeline_override_version},
            }
        }
        fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(platform_config))

        result = PlatformHelperVersioning()._resolve_required_version(
            "main", version_status=PlatformHelperVersioning().get_version_status()
        )

        assert result == pipeline_override_version


@patch("requests.get")
@patch("dbt_platform_helper.providers.version.version")
def test_get_required_version_errors_if_version_is_not_specified(
    mock_version,
    mock_get,
    mock_io_provider,
    fakefs,
):
    mock_version.return_value = "1.2.3"
    mock_get.return_value.json.return_value = {
        "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
    }

    platform_config_without_default_version = {"application": "my-app"}
    fakefs.create_file(
        PLATFORM_CONFIG_FILE, contents=yaml.dump(platform_config_without_default_version)
    )

    expected_message = f"""Cannot get dbt-platform-helper version from '{PLATFORM_CONFIG_FILE}'.
Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n  platform-helper: 1.2.3
"""

    with pytest.raises(PlatformHelperVersionNotFoundException):
        PlatformHelperVersioning(io=mock_io_provider).get_required_version()

    mock_io_provider.process_messages.assert_called_with(
        {"warnings": [], "errors": [expected_message]}
    )


# TODO this is testing both get_required_platform_helper_version and
# get_platform_helper_version_status.  We should instead unit test
# PlatformHelperVersion.get_status thoroughly and then inject VersionStatus for this test.
@pytest.mark.parametrize(
    "platform_helper_version_file_version,platform_config_default_version,expected_version",
    [
        ("0.0.1", None, "0.0.1"),
        ("0.0.1", "1.0.0", "1.0.0"),
    ],
)
@patch("dbt_platform_helper.providers.version.version", return_value="0.0.0")
@patch("requests.get")
def test_get_required_platform_helper_version(
    mock_get,
    mock_version,
    fakefs,
    platform_helper_version_file_version,
    platform_config_default_version,
    expected_version,
):
    mock_get.return_value.json.return_value = {
        "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
    }
    if platform_helper_version_file_version:
        Path(PLATFORM_HELPER_VERSION_FILE).write_text("0.0.1")

    platform_config = {
        "application": "my-app",
        "environments": {"dev": None},
        "environment_pipelines": {
            "main": {"slack_channel": "abc", "trigger_on_push": True, "environments": {"dev": None}}
        },
    }
    if platform_config_default_version:
        platform_config["default_versions"] = {"platform-helper": platform_config_default_version}

    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(platform_config))

    version_status = PlatformHelperVersioning().get_version_status()
    required_version = PlatformHelperVersioning()

    result = required_version._resolve_required_version(version_status=version_status)

    assert result == expected_version


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
# TODO add coverage for the include_project_versions parameter in the PlatformHelperVersion tests
@patch("requests.get")
@patch("dbt_platform_helper.providers.version.version")
def test_platform_helper_version_deprecation_warnings(
    mock_version,
    mock_get,
    mock_io_provider,
    fakefs,
    version_in_phv_file,
    version_in_platform_config,
    expected_warnings,
):
    mock_version.return_value = "1.2.3"
    mock_get.return_value.json.return_value = {
        "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
    }
    platform_config = {"application": "my-app"}
    if version_in_platform_config:
        platform_config["default_versions"] = {"platform-helper": "2.2.2"}

    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(platform_config))

    if version_in_phv_file:
        fakefs.create_file(PLATFORM_HELPER_VERSION_FILE, contents="3.3.3")

    PlatformHelperVersioning(io=mock_io_provider).get_required_version()

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
