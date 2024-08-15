import os
from pathlib import Path
from typing import Tuple
from typing import Type
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.exceptions import IncompatibleMajorVersion
from dbt_platform_helper.exceptions import IncompatibleMinorVersion
from dbt_platform_helper.exceptions import ValidationException
from dbt_platform_helper.utils.versioning import PlatformHelperVersions
from dbt_platform_helper.utils.versioning import check_platform_helper_version_mismatch
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)
from dbt_platform_helper.utils.versioning import get_aws_versions
from dbt_platform_helper.utils.versioning import get_copilot_versions
from dbt_platform_helper.utils.versioning import get_github_released_version
from dbt_platform_helper.utils.versioning import get_platform_helper_versions
from dbt_platform_helper.utils.versioning import get_required_platform_helper_version
from dbt_platform_helper.utils.versioning import parse_version
from dbt_platform_helper.utils.versioning import string_version
from dbt_platform_helper.utils.versioning import validate_template_version
from dbt_platform_helper.utils.versioning import validate_version_compatibility
from tests.platform_helper.conftest import FIXTURES_DIR


@pytest.mark.parametrize(
    "suite",
    [
        ("v1.2.3", (1, 2, 3)),
        ("1.2.3", (1, 2, 3)),
        ("v0.1-TEST", (0, 1, -1)),
        ("TEST-0.2", (-1, 0, 2)),
        ("unknown", None),
        (None, None),
    ],
)
def test_parsing_version_numbers(suite):
    input_version, expected_version = suite
    assert parse_version(input_version) == expected_version


@pytest.mark.parametrize(
    "suite",
    [
        ((1, 2, 3), "1.2.3"),
        ((0, 1, -1), "0.1.-1"),
        ((-1, 0, 2), "-1.0.2"),
        (None, "unknown"),
    ],
)
def test_stringify_version_numbers(suite):
    input_version, expected_version = suite
    assert string_version(input_version) == expected_version


class MockGithubReleaseResponse:
    @staticmethod
    def json():
        return {"tag_name": "1.1.1"}


@patch("requests.get", return_value=MockGithubReleaseResponse())
def test_get_github_version_from_releases(request_get):
    assert get_github_released_version("test/repo") == (1, 1, 1)
    request_get.assert_called_once_with("https://api.github.com/repos/test/repo/releases/latest")


class MockGithubTagResponse:
    @staticmethod
    def json():
        return [{"name": "1.1.1"}, {"name": "1.2.3"}]


@patch("requests.get", return_value=MockGithubTagResponse())
def test_get_github_version_from_tags(request_get):
    assert get_github_released_version("test/repo", True) == (1, 2, 3)
    request_get.assert_called_once_with("https://api.github.com/repos/test/repo/tags")


@pytest.mark.parametrize(
    "version_check",
    [
        ((1, 40, 0), (1, 30, 0), IncompatibleMinorVersion),
        ((1, 40, 0), (2, 1, 0), IncompatibleMajorVersion),
        ((0, 2, 40), (0, 1, 30), IncompatibleMajorVersion),
        ((0, 1, 40), (0, 1, 30), IncompatibleMajorVersion),
    ],
)
def test_validate_version_compatability(
    version_check: Tuple[
        Tuple[int, int, int],
        Tuple[int, int, int],
        Type[BaseException],
    ]
):
    app_version, check_version, raises = version_check

    with pytest.raises(raises):
        validate_version_compatibility(app_version, check_version)


@pytest.mark.parametrize(
    "template_check",
    [
        ("addon_newer_major_version.yml", IncompatibleMajorVersion, ""),
        ("addon_newer_minor_version.yml", IncompatibleMinorVersion, ""),
        ("addon_older_major_version.yml", IncompatibleMajorVersion, ""),
        ("addon_older_minor_version.yml", IncompatibleMinorVersion, ""),
        ("addon_no_version.yml", ValidationException, "Template %s has no version information"),
    ],
)
def test_validate_template_version(template_check: Tuple[str, Type[BaseException], str]):
    template_name, raises, message = template_check

    with pytest.raises(raises) as exception:
        template_path = str(Path(f"{FIXTURES_DIR}/version_validation/{template_name}").resolve())
        validate_template_version((10, 10, 10), template_path)

    if message:
        assert (message % template_path) == str(exception.value)


@pytest.mark.parametrize(
    "expected_exception",
    [
        IncompatibleMajorVersion,
        IncompatibleMinorVersion,
        IncompatibleMinorVersion,
    ],
)
@patch("click.secho")
@patch("click.confirm")
@patch("dbt_platform_helper.utils.versioning.get_platform_helper_versions")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_platform_helper.utils.versioning.validate_version_compatibility")
def test_check_platform_helper_version_needs_update(
    version_compatibility, mock_get_platform_helper_versions, confirm, secho, expected_exception
):
    mock_get_platform_helper_versions.return_value = PlatformHelperVersions((1, 0, 0), (1, 0, 0))
    version_compatibility.side_effect = expected_exception((1, 0, 0), (1, 0, 0))

    check_platform_helper_version_needs_update()

    if expected_exception == IncompatibleMajorVersion:
        secho.assert_called_with(
            "You are running platform-helper v1.0.0, upgrade to v1.0.0 by running run `pip install "
            "--upgrade dbt-platform-helper`.",
            fg="red",
        )

    if expected_exception == IncompatibleMinorVersion:
        secho.assert_called_with(
            "You are running platform-helper v1.0.0, upgrade to v1.0.0 by running run `pip install "
            "--upgrade dbt-platform-helper`.",
            fg="yellow",
        )


@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=False),
)
@patch("dbt_platform_helper.utils.versioning.validate_version_compatibility")
def test_check_platform_helper_version_skips_when_running_local_version(version_compatibility):
    check_platform_helper_version_needs_update()

    version_compatibility.assert_not_called()


@patch("click.secho")
@patch("dbt_platform_helper.utils.versioning.get_platform_helper_versions")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
def test_check_platform_helper_version_shows_warning_when_different_than_file_spec(
    get_file_app_versions, secho
):
    get_file_app_versions.return_value = PlatformHelperVersions(
        local_version=(1, 0, 1), platform_helper_file_version=(1, 0, 0)
    )

    check_platform_helper_version_mismatch()

    secho.assert_called_with(
        f"WARNING: You are running platform-helper v1.0.1 against v1.0.0 specified by {PLATFORM_HELPER_VERSION_FILE}.",
        fg="red",
    )


@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=True),
)
@patch("dbt_platform_helper.utils.versioning.validate_version_compatibility")
def test_check_platform_helper_version_skips_when_skip_environment_variable_is_set(
    version_compatibility,
):
    os.environ["PLATFORM_TOOLS_SKIP_VERSION_CHECK"] = "true"

    check_platform_helper_version_needs_update()

    version_compatibility.assert_not_called()


@patch("requests.get")
@patch("dbt_platform_helper.utils.versioning.version")
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
def test_get_platform_helper_versions(
    mock_aws, mock_version, mock_get, fakefs, valid_platform_config
):
    mock_version.return_value = "1.1.1"
    mock_get.return_value.json.return_value = {
        "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
    }
    fakefs.create_file(PLATFORM_HELPER_VERSION_FILE, contents="5.6.7")
    config = valid_platform_config
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(config))

    versions = get_platform_helper_versions()

    assert versions.local_version == (1, 1, 1)
    assert versions.latest_release == (2, 3, 4)
    assert versions.platform_helper_file_version == (5, 6, 7)
    assert versions.platform_config_default == (10, 2, 0)
    assert versions.pipeline_overrides == {"test": "main", "prod-main": "9.0.9"}
    assert not mock_aws.called  # Ensure that an AWS session is not required for this function


@pytest.mark.parametrize(
    "version_in_phv_file, version_in_platform_config, expected_warning",
    (
        (
            False,
            False,
            f"Cannot get dbt-platform-helper version from '{PLATFORM_CONFIG_FILE}'.\n"
            f"Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n  platform-helper: 1.2.3\n",
        ),
        (
            True,
            False,
            f"Please delete '{PLATFORM_HELPER_VERSION_FILE}' as it is now deprecated.\n"
            f"Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n"
            "  platform-helper: 3.3.3\n",
        ),
        (False, True, None),
        (True, True, f"Please delete '{PLATFORM_HELPER_VERSION_FILE}' as it is now deprecated."),
    ),
)
@patch("click.secho")
@patch("requests.get")
@patch("dbt_platform_helper.utils.versioning.version")
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
def test_platform_helper_version_warnings(
    mock_aws,
    mock_version,
    mock_get,
    secho,
    fakefs,
    version_in_phv_file,
    version_in_platform_config,
    expected_warning,
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

    get_platform_helper_versions()

    if expected_warning:
        secho.assert_called_with(expected_warning, fg="yellow")
    else:
        secho.assert_not_called()


@patch("subprocess.run")
@patch("dbt_platform_helper.utils.versioning.get_github_released_version", return_value=(2, 0, 0))
def test_get_copilot_versions(mock_get_github_released_version, mock_run):
    mock_run.return_value.stdout = b"1.0.0"

    versions = get_copilot_versions()

    assert versions.local_version == (1, 0, 0)
    assert versions.latest_release == (2, 0, 0)


@patch("subprocess.run")
@patch("dbt_platform_helper.utils.versioning.get_github_released_version", return_value=(2, 0, 0))
def test_get_aws_versions(mock_get_github_released_version, mock_run):
    mock_run.return_value.stdout = b"aws-cli/1.0.0"
    versions = get_aws_versions()

    assert versions.local_version == (1, 0, 0)
    assert versions.latest_release == (2, 0, 0)


@pytest.mark.parametrize(
    "platform_helper_version_file_version,platform_config_default_version,expected_version",
    [
        (None, None, None),
        ("0.0.1", None, "0.0.1"),
        ("0.0.1", "1.0.0", "1.0.0"),
    ],
)
@patch("dbt_platform_helper.utils.versioning.version", return_value="0.0.0")
@patch("requests.get")
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort", new=Mock())
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

    required_version = get_required_platform_helper_version()

    assert required_version == expected_version


@pytest.mark.parametrize(
    "platform_helper_version_file_version, platform_config_default_version, pipeline_override, expected_version",
    [
        (None, None, None, None),
        ("0.0.1", None, None, "0.0.1"),
        ("0.0.1", "1.0.0", None, "1.0.0"),
        (None, None, "2.0.0", "2.0.0"),
        (None, "3.0.0", "4.0.0", "4.0.0"),
        ("0.0.1", "4.0.0", "5.0.0", "5.0.0"),
    ],
)
@patch("dbt_platform_helper.utils.versioning.version", return_value="0.0.0")
@patch("requests.get")
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort", new=Mock())
def test_get_required_platform_helper_version_in_pipeline(
    mock_get,
    mock_version,
    fakefs,
    platform_helper_version_file_version,
    platform_config_default_version,
    pipeline_override,
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

    if pipeline_override:
        platform_config["environment_pipelines"]["main"]["versions"] = {
            "platform-helper": pipeline_override
        }

    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(platform_config))

    required_version = get_required_platform_helper_version("main")

    assert required_version == expected_version
