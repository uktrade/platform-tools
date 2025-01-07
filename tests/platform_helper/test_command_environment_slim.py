from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.environment import generate_terraform


class TestMaintenancePage:
    pass


class TestGenerateCopilot:
    pass


class TestGenerateTerraform:
    @patch("dbt_platform_helper.commands.environment.ConfigProvider")
    @patch("dbt_platform_helper.commands.environment.TerraformEnvironment")
    def test_generate_terraform_success(self, terraform_environment_mock, config_provider_mock):
        """Test that given name and terraform-platform-modules-version, the
        generate terraform command calls TerraformEnvironment generate with app,
        env, addon type and addon name."""

        mock_terraform_environment_instance = terraform_environment_mock.return_value

        result = CliRunner().invoke(
            generate_terraform,
            ["--name", "test", "--terraform-platform-modules-version", "123"],
        )

        assert result.exit_code == 0

        mock_terraform_environment_instance.generate.assert_called_with("test", "123")

    def test_generate_terraform_raises_exception_in_case_of_failure(self):
        pass
