import os
from pathlib import Path
from typing import Tuple
from typing import Type
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from dbt_platform_helper.exceptions import IncompatibleMajorVersion
from dbt_platform_helper.exceptions import IncompatibleMinorVersion
from dbt_platform_helper.exceptions import ValidationException
from dbt_platform_helper.utils.versioning import PlatformHelperVersions
from dbt_platform_helper.utils.versioning import check_platform_helper_version_mismatch
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)
from dbt_platform_helper.utils.versioning import get_github_released_version
from dbt_platform_helper.utils.versioning import get_platform_helper_versions
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
        f"WARNING: You are running platform-helper v1.0.1 against v1.0.0 specified by .platform-helper-version.",
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
def test_get_platform_helper_versions(mock_version, mock_get, fakefs):
    mock_version.return_value = "1.2.3"
    mock_get.return_value.json.return_value = {
        "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
    }
    fakefs.create_file(".platform-helper-version", contents="5.6.7")

    versions = get_platform_helper_versions()

    assert versions.local_version == (1, 2, 3)
    assert versions.latest_release == (2, 3, 4)
    assert versions.platform_helper_file_version == (5, 6, 7)


@patch("click.secho")
@patch("requests.get")
@patch("dbt_platform_helper.utils.versioning.version")
def test_platform_helper_version_file_does_not_exist(mock_version, mock_get, secho):
    mock_version.return_value = "1.2.3"
    mock_get.return_value.json.return_value = {
        "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
    }

    if os.path.exists(".platform-helper-version"):
        os.remove(".platform-helper-version")

    versions = get_platform_helper_versions()

    assert versions.platform_helper_file_version is None
    secho.assert_called_with(
        f"Cannot get dbt-platform-helper version from file '.platform-helper-version'. Check if file exists.",
        fg="yellow",
    )


def test_get_copilot_versions():
    pass


def test_get_aws_versions():
    pass
