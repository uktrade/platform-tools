import pytest

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.domain.terraform_versioning import TerraformVersioning


class TestTerraformVersioning:
    def test_get_required_version(self):
        pass

    @pytest.mark.parametrize(
        "cli_terraform_platform_version, config_terraform_platform_version, expected_version",
        [
            ("feature_branch", "5", "feature_branch"),
            (None, "5", "5"),
            (None, None, DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION),
        ],
    )
    def test_determine_terraform_platform_modules_version(
        self, cli_terraform_platform_version, config_terraform_platform_version, expected_version
    ):
        assert (
            TerraformVersioning().get_required_terraform_platform_modules_version(
                cli_terraform_platform_version, config_terraform_platform_version
            )
            == expected_version
        )
