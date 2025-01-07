from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.environment import generate
from dbt_platform_helper.commands.environment import generate_terraform
from dbt_platform_helper.commands.environment import offline
from dbt_platform_helper.commands.environment import online
from dbt_platform_helper.platform_exception import PlatformException


class TestMaintenancePage:

    @patch("dbt_platform_helper.commands.environment.MaintenancePage")
    def test_online_success(self, mock_maintenance_page):
        """Test that given a app name and a environment, the maintenenace page
        deactivate() method is called with the given app and environment."""

        mock_maintenance_page_instance = mock_maintenance_page.return_value

        result = CliRunner().invoke(
            online,
            ["--app", "test-app", "--env", "test-env"],
        )

        assert result.exit_code == 0
        mock_maintenance_page_instance.deactivate.assert_called_with("test-app", "test-env")

    @patch("dbt_platform_helper.commands.environment.MaintenancePage")
    @patch("click.secho")
    def test_online_failure(self, mock_click, mock_maintenance_page):
        """Test that given a app name and a environment, and the online() raises
        a PlatformException, the error is caught and the error message is
        returned."""

        mock_maintenance_page_instance = mock_maintenance_page.return_value
        mock_maintenance_page_instance.deactivate.side_effect = PlatformException("i've failed")

        result = CliRunner().invoke(
            online,
            ["--app", "test-app", "--env", "test-env"],
        )

        assert result.exit_code == 1
        mock_click.assert_called_with("""i've failed""", fg="red")
        mock_maintenance_page_instance.deactivate.assert_called_with("test-app", "test-env")

    @patch("dbt_platform_helper.commands.environment.MaintenancePage")
    def test_offline_success(self, mock_maintenance_page):
        """Test that given a app name, environment, service name, page template
        and vpc, the maintenenace page activate() method is called with the
        given parameters."""

        mock_maintenance_page_instance = mock_maintenance_page.return_value

        result = CliRunner().invoke(
            offline,
            [
                "--app",
                "test-app",
                "--env",
                "test-env",
                "--svc",
                "test-svc",
                "--template",
                "default",
                "--vpc",
                "test-vpc",
            ],
        )

        assert result.exit_code == 0
        mock_maintenance_page_instance.activate.assert_called_with(
            "test-app", "test-env", ("test-svc",), "default", "test-vpc"
        )

    @patch("dbt_platform_helper.commands.environment.MaintenancePage")
    @patch("click.secho")
    def test_offline_failure(self, mock_click, mock_maintenance_page):
        """Test that given a app name, environment, service name, page template
        and vpc, and the offline() method raises a PlatformException, the error
        is caught and the error message is returned."""

        mock_maintenance_page_instance = mock_maintenance_page.return_value
        mock_maintenance_page_instance.activate.side_effect = PlatformException("i've failed")

        result = CliRunner().invoke(
            offline,
            [
                "--app",
                "test-app",
                "--env",
                "test-env",
                "--svc",
                "test-svc",
                "--template",
                "default",
                "--vpc",
                "test-vpc",
            ],
        )

        assert result.exit_code == 1
        mock_click.assert_called_with("""i've failed""", fg="red")
        mock_maintenance_page_instance.activate.assert_called_with(
            "test-app", "test-env", ("test-svc",), "default", "test-vpc"
        )


class TestGenerateCopilot:

    @patch("dbt_platform_helper.commands.environment.ConfigProvider")
    @patch("dbt_platform_helper.commands.environment.CopilotEnvironment")
    def test_generate_copilot_success(self, copilot_environment_mock, config_provider_mock):
        """Test that given name and terraform-platform-modules-version, the
        generate terraform command calls CopilotEnvironment generate with app,
        env, addon type and addon name."""

        mock_copilot_environment_instance = copilot_environment_mock.return_value

        result = CliRunner().invoke(
            generate,
            ["--name", "test"],
        )

        assert result.exit_code == 0
        mock_copilot_environment_instance.generate.assert_called_with("test")

    @patch("dbt_platform_helper.commands.environment.ConfigProvider")
    @patch("dbt_platform_helper.commands.environment.CopilotEnvironment")
    @patch("click.secho")
    def test_generate_copilot_catches_platform_exception_and_exits(
        self, mock_click, copilot_environment_mock, config_provider_mock
    ):
        """Test that given name and terraform-platform-modules-version, the
        generate terraform command calls CopilotEnvironment generate with app,
        env, addon type and addon name."""

        mock_copilot_environment_instance = copilot_environment_mock.return_value
        mock_copilot_environment_instance.generate.side_effect = PlatformException("i've failed")

        result = CliRunner().invoke(
            generate,
            ["--name", "test"],
        )

        assert result.exit_code == 1
        mock_copilot_environment_instance.generate.assert_called_with("test")
        mock_click.assert_called_with("""i've failed""", fg="red")


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
