from pathlib import Path
from typing import Tuple
from typing import Type
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from dbt_copilot_helper.exceptions import IncompatibleMajorVersion
from dbt_copilot_helper.exceptions import IncompatibleMinorVersion
from dbt_copilot_helper.exceptions import ValidationException
from dbt_copilot_helper.utils.versioning import (
    check_copilot_helper_version_needs_update,
)
from dbt_copilot_helper.utils.versioning import get_github_released_version
from dbt_copilot_helper.utils.versioning import parse_version
from dbt_copilot_helper.utils.versioning import string_version
from dbt_copilot_helper.utils.versioning import validate_template_version
from dbt_copilot_helper.utils.versioning import validate_version_compatibility
from tests.copilot_helper.conftest import FIXTURES_DIR


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
@patch("dbt_copilot_helper.utils.versioning.get_app_versions")
@patch(
    "dbt_copilot_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_copilot_helper.utils.versioning.validate_version_compatibility")
def test_check_copilot_helper_version_needs_update(
    version_compatibility, get_app_versions, confirm, secho, expected_exception
):
    get_app_versions.return_value = (1, 0, 0), (1, 0, 0)
    version_compatibility.side_effect = expected_exception((1, 0, 0), (1, 0, 0))

    check_copilot_helper_version_needs_update()

    if expected_exception == IncompatibleMajorVersion:
        secho.assert_called_with(
            "You are running copilot-helper v1.0.0, upgrade to v1.0.0 by running run `pip install "
            "--upgrade dbt-platform-tools`.",
            fg="red",
        )

    if expected_exception == IncompatibleMinorVersion:
        secho.assert_called_with(
            "You are running copilot-helper v1.0.0, upgrade to v1.0.0 by running run `pip install "
            "--upgrade dbt-platform-tools`.",
            fg="yellow",
        )


@patch(
    "dbt_copilot_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=False)
)
@patch("dbt_copilot_helper.utils.versioning.validate_version_compatibility")
def test_check_copilot_helper_version_skips_when_running_local_version(version_compatibility):
    check_copilot_helper_version_needs_update()

    version_compatibility.assert_not_called()
