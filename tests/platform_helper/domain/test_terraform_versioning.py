import pytest

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.domain.terraform_versioning import (
    TerraformPlatformModulesVersioning,
)


class TestTerraformPlatformModulesVersioning:
    @pytest.mark.parametrize(
        "cli_terraform_platform_version, config_terraform_platform_version, expected_version",
        [
            ("feature_branch", "5", "feature_branch"),
            (None, "5", "5"),
            (None, None, DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION),
        ],
    )
    def test_get_required_version(
        self, cli_terraform_platform_version, config_terraform_platform_version, expected_version
    ):
        assert (
            TerraformPlatformModulesVersioning().get_required_version(
                cli_terraform_platform_version, config_terraform_platform_version
            )
            == expected_version
        )
