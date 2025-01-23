from unittest.mock import Mock
from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.environment import generate
from dbt_platform_helper.commands.environment import generate_terraform
from dbt_platform_helper.commands.environment import offline
from dbt_platform_helper.commands.environment import online
from dbt_platform_helper.platform_exception import PlatformException


class TestMaintenancePage:

    @patch("dbt_platform_helper.commands.environment.MaintenancePage")
    @patch("dbt_platform_helper.commands.environment.load_application")
    def test_online_success(self, load_application, mock_maintenance_page, mock_application):
        """Test that given a app name and a environment, the maintenenace page
        deactivate() method is called with the given app and environment."""

        load_application.return_value = mock_application
        mock_maintenance_page_instance = mock_maintenance_page.return_value

        result = CliRunner().invoke(
            online,
            ["--app", "test-app", "--env", "test-env"],
        )

        assert result.exit_code == 0
        mock_maintenance_page.assert_called_with(mock_application)
        mock_maintenance_page_instance.deactivate.assert_called_with("test-env")

    @patch("dbt_platform_helper.commands.environment.MaintenancePage")
    @patch("click.secho")
    @patch("dbt_platform_helper.commands.environment.load_application")
    def test_online_failure(
        self, load_application, mock_click, mock_maintenance_page, mock_application
    ):
        """Test that given a app name and a environment, and the online() raises
        a PlatformException, the error is caught and the error message is
        returned."""

        load_application.return_value = mock_application
        mock_maintenance_page_instance = mock_maintenance_page.return_value
        mock_maintenance_page_instance.deactivate.side_effect = PlatformException("i've failed")

        result = CliRunner().invoke(
            online,
            ["--app", "test-app", "--env", "test-env"],
        )

        assert result.exit_code == 1
        mock_click.assert_called_with("""i've failed""", fg="red")
        mock_maintenance_page.assert_called_with(mock_application)
        mock_maintenance_page_instance.deactivate.assert_called_with("test-env")

    @patch("dbt_platform_helper.commands.environment.MaintenancePage")
    @patch("dbt_platform_helper.commands.environment.load_application")
    def test_offline_success(self, load_application, mock_maintenance_page, mock_application):
        """Test that given a app name, environment, service name, page template
        and vpc, the maintenenace page activate() method is called with the
        given parameters."""

        load_application.return_value = mock_application
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
        mock_maintenance_page.assert_called_with(mock_application)
        mock_maintenance_page_instance.activate.assert_called_with(
            "test-env", ("test-svc",), "default", "test-vpc"
        )

    @patch("dbt_platform_helper.commands.environment.MaintenancePage")
    @patch("click.secho")
    @patch("dbt_platform_helper.commands.environment.load_application")
    def test_offline_failure(
        self, load_application, mock_click, mock_maintenance_page, mock_application
    ):
        """Test that given a app name, environment, service name, page template
        and vpc, and the offline() method raises a PlatformException, the error
        is caught and the error message is returned."""
        load_application.return_value = mock_application
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
        mock_maintenance_page.assert_called_with(mock_application)
        mock_maintenance_page_instance.activate.assert_called_with(
            "test-env", ("test-svc",), "default", "test-vpc"
        )


class TestGenerateCopilot:

    @patch("dbt_platform_helper.commands.environment.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.environment.ConfigProvider")
    @patch("dbt_platform_helper.commands.environment.ConfigValidator")
    @patch("dbt_platform_helper.commands.environment.VpcProvider")
    @patch("dbt_platform_helper.commands.environment.CloudFormation")
    @patch("dbt_platform_helper.commands.environment.CopilotEnvironment")
    def test_generate_copilot_success(
        self,
        copilot_environment_mock,
        cloudformation_provider_mock,
        mock_vpc_provider,
        mock_config_validator,
        mock_config_provider,
        mock_session,
    ):
        """Test that given a environment name, the generate command calls
        CopilotEnvironment.generate with the environment name."""
        mock_session.return_value = Mock()
        mock_config_validator.return_value = Mock()

        result = CliRunner().invoke(
            generate,
            ["--name", "test"],
        )

        assert result.exit_code == 0

        copilot_environment_mock.return_value.generate.assert_called_with("test")
        mock_vpc_provider.assert_called_once_with(mock_session.return_value)
        mock_config_validator.assert_called_once_with()
        mock_config_provider.assert_called_once_with(mock_config_validator.return_value)
        copilot_environment_mock.assert_called_once_with(
            mock_config_provider.return_value,
            mock_vpc_provider.return_value,
            cloudformation_provider_mock.return_value,
            mock_session.return_value,
        )

    @patch("dbt_platform_helper.commands.environment.CopilotEnvironment")
    @patch("dbt_platform_helper.commands.environment.get_aws_session_or_abort")
    @patch("click.secho")
    def test_generate_copilot_catches_platform_exception_and_exits(
        self, mock_click, mock_session, copilot_environment_mock
    ):
        """
        Test that given environment name and the CopilotEnvironment generate
        raises a PlatformException,

        The exception is caught and the command exits.
        """

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
    @patch("dbt_platform_helper.commands.environment.TerraformEnvironment")
    def test_generate_terraform_success(self, terraform_environment_mock):
        """Test that given name and terraform-platform-modules-version, the
        generate terraform command calls TerraformEnvironment generate with the
        expected parameters."""

        mock_terraform_environment_instance = terraform_environment_mock.return_value

        result = CliRunner().invoke(
            generate_terraform,
            ["--name", "test", "--terraform-platform-modules-version", "123"],
        )

        assert result.exit_code == 0

        mock_terraform_environment_instance.generate.assert_called_with("test", "123")

    @patch("dbt_platform_helper.commands.environment.TerraformEnvironment")
    def test_generate_terraform_without_version_flag_success(self, terraform_environment_mock):
        """Test that given name, the generate terraform command calls
        TerraformEnvironment generate with the expected parameters."""

        mock_terraform_environment_instance = terraform_environment_mock.return_value

        result = CliRunner().invoke(
            generate_terraform,
            ["--name", "test"],
        )

        assert result.exit_code == 0

        mock_terraform_environment_instance.generate.assert_called_with("test", None)

    @patch("dbt_platform_helper.commands.environment.TerraformEnvironment")
    @patch("click.secho")
    def test_generate_terraform_catches_platform_exception_and_exits(
        self, mock_click, terraform_environment_mock
    ):
        """Test that given generate raises an exception, the exception is caught
        and the command exits."""

        mock_terraform_environment_instance = terraform_environment_mock.return_value
        mock_terraform_environment_instance.generate.side_effect = PlatformException("i've failed")

        result = CliRunner().invoke(
            generate_terraform,
            ["--name", "test", "--terraform-platform-modules-version", "123"],
        )

        assert result.exit_code == 1
        mock_click.assert_called_with("""i've failed""", fg="red")
        mock_terraform_environment_instance.generate.assert_called_with("test", "123")
