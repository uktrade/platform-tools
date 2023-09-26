from pathlib import Path
from typing import Tuple
from typing import Type

import pytest

from dbt_copilot_helper.exceptions import IncompatibleMajorVersion
from dbt_copilot_helper.exceptions import IncompatibleMinorVersion
from dbt_copilot_helper.exceptions import ValidationException
from dbt_copilot_helper.utils.versioning import parse_version
from dbt_copilot_helper.utils.versioning import validate_template_version
from dbt_copilot_helper.utils.versioning import validate_version_compatibility


@pytest.mark.parametrize(
    "suite",
    [
        ("v1.2.3", (1, 2, 3)),
        ("1.2.3", (1, 2, 3)),
        ("v0.1-TEST", (0, 1, -1)),
        ("TEST-0.2", (-1, 0, 2)),
    ],
)
def test_parsing_version_numbers(suite):
    input_version, expected_version = suite
    assert parse_version(input_version) == expected_version


class MockVersionResponse:
    @staticmethod
    def json():
        return {
            "releases": {
                "2.0-rc1": {},
                "1.0.0": {},
                "1.0.3": {},
                "0.1.49": {},
                "0.1.46": {},
            }
        }


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
        ("addon_newer_major_version.yml", IncompatibleMajorVersion, None),
        ("addon_newer_minor_version.yml", IncompatibleMinorVersion, None),
        ("addon_older_major_version.yml", IncompatibleMajorVersion, None),
        ("addon_older_minor_version.yml", IncompatibleMinorVersion, None),
        ("addon_no_version.yml", ValidationException, "Template %s has no version information"),
    ],
)
def test_validate_template_version(template_check: Tuple[str, Type[BaseException], str | None]):
    template_name, raises, message = template_check

    with pytest.raises(raises) as exception:
        template_path = str(Path(f"../fixtures/version_validation/{template_name}").resolve())
        validate_template_version((10, 10, 10), template_path)

    if message is not None:
        assert (message % template_path) == str(exception.value)
