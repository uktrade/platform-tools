import pytest

from dbt_platform_helper.constants import DEFAULT_PLATFORM_HELPER_VERSION
from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.utils.tool_versioning import (
    get_required_platform_helper_version,
)
from dbt_platform_helper.utils.tool_versioning import (
    get_required_terraform_platform_modules_version,
)

@pytest.mark.parametrize(
   "cli_version, config_version, expected",
   [
       ("13.0.0", "12.0.0", "13.0.0"),
       (None, "12.0.0", "12.0.0"),
       (None, None, DEFAULT_PLATFORM_HELPER_VERSION),
       (None, "", DEFAULT_PLATFORM_HELPER_VERSION),
       ("", "12.0.0", "12.0.0"),
       ("", "", DEFAULT_PLATFORM_HELPER_VERSION),
       ("13.0.0", None, "13.0.0"),
       ("", None, DEFAULT_PLATFORM_HELPER_VERSION),
   ],
)
def test_get_required_platform_helper_version(cli_version, config_version, expected):
   result = get_required_platform_helper_version(cli_version, config_version)
   assert result == expected, f"Expected {expected}, but got {result}"

@pytest.mark.parametrize(
    "cli_terraform_platform_version, config_terraform_platform_version, expected_version",
    [
        ("feature_branch", "5", "feature_branch"),
        (None, "5", "5"),
        (None, None, DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION),
    ],
)
def test_determine_terraform_platform_modules_version(
    cli_terraform_platform_version, config_terraform_platform_version, expected_version
):
    assert (
        get_required_terraform_platform_modules_version(
            cli_terraform_platform_version, config_terraform_platform_version
        )
        == expected_version
    )
