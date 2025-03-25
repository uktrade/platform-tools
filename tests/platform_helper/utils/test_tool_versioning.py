import pytest

from dbt_platform_helper.utils.tool_versioning import (
    get_required_platform_helper_version,
)


@pytest.mark.parametrize(
    "cli_version, config_version, expected",
    [
        ("13.0.0", "12.0.0", "13.0.0"),
        (None, "12.0.0", "12.0.0"),
        ("", "12.0.0", "12.0.0"),
        ("13.0.0", None, "13.0.0"),
    ],
)
def test_get_required_platform_helper_version(cli_version, config_version, expected):
    result = get_required_platform_helper_version(cli_version, config_version)
    assert result == expected, f"Expected {expected}, but got {result}"
