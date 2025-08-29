from unittest.mock import patch

from click.testing import CliRunner
from moto import mock_aws

from dbt_platform_helper.commands.service import generate
from dbt_platform_helper.domain.service import EnvironmentNotFoundException


class TestGenerateTerraform:
    @mock_aws
    @patch("dbt_platform_helper.commands.service.ServiceManager")
    def test_generate_success(self, mock_service_manager):
        """Test that given name, environment, and image tag, the service
        generate command calls ServiceManager generate with the expected
        parameters."""

        mock_terraform_service_instance = mock_service_manager.return_value

        result = CliRunner().invoke(
            generate,
            ["--name", "web", "--environment", "dev", "--image-tag", "test123"],
        )

        assert result.exit_code == 0

        mock_terraform_service_instance.generate.assert_called_with(
            environment="dev", services=["web"], image_tag_flag="test123"
        )

    @mock_aws
    @patch("dbt_platform_helper.commands.service.ServiceManager")
    @patch("dbt_platform_helper.commands.service.click.secho")
    def test_generate_catches_platform_exception_and_exits(self, mock_click, mock_service_manager):
        """Test that given incorrect arguments generate raises an exception, the
        exception is caught and the command exits."""

        mock_instance = mock_service_manager.return_value
        mock_instance.generate.side_effect = EnvironmentNotFoundException("bad env")

        result = CliRunner().invoke(
            generate,
            ["--environment", "bad-env"],
        )

        assert result.exit_code == 1
        mock_click.assert_called_with("Error: bad env", err=True, fg="red")
