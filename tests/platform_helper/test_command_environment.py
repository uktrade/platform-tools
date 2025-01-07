from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.environment import generate_terraform
from dbt_platform_helper.platform_exception import PlatformException


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

    @patch("dbt_platform_helper.commands.environment.ConfigProvider")
    @patch("dbt_platform_helper.commands.environment.TerraformEnvironment")
    @patch("click.secho")
    def test_generate_terraform_catches_platform_exception_and_exits(
        self, mock_click, terraform_environment_mock, config_provider_mock
    ):
        """
        Test that given name and terraform-platform-modules-version and the
        generate raises an exception.

        The exception is caught and the command exits.
        """

        mock_terraform_environment_instance = terraform_environment_mock.return_value
        mock_terraform_environment_instance.generate.side_effect = PlatformException("i've failed")

        result = CliRunner().invoke(
            generate_terraform,
            ["--name", "test", "--terraform-platform-modules-version", "123"],
        )

        assert result.exit_code == 1
        mock_click.assert_called_with("""i've failed""", fg="red")
        mock_terraform_environment_instance.generate.assert_called_with("test", "123")
