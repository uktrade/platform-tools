from unittest.mock import Mock
from unittest.mock import patch

from click.testing import CliRunner
from moto import mock_aws

from dbt_platform_helper.commands.internal import internal
from dbt_platform_helper.domain.terraform_environment import (
    EnvironmentNotFoundException,
)
from dbt_platform_helper.platform_exception import PlatformException


class TestInternal:
    @patch("dbt_platform_helper.commands.internal.ServiceManager")
    @patch("dbt_platform_helper.commands.internal.ECS")
    @patch("dbt_platform_helper.commands.internal.LogsProvider")
    @patch("dbt_platform_helper.commands.internal.S3Provider")
    @patch("dbt_platform_helper.commands.internal.load_application")
    @patch("dbt_platform_helper.commands.internal.ConfigProvider")
    @patch("dbt_platform_helper.commands.internal.ConfigValidator")
    def test_service_deploy_success(
        self,
        mock_config_validator,
        mock_config_provider,
        mock_load_application,
        mock_s3_provider,
        mock_logs_provider,
        mock_ecs_provider,
        mock_service_manager,
    ):

        mock_config_provider.return_value.get_enriched_config.return_value = {
            "application": "myapp"
        }

        # Mock AWS calls
        mock_ecs_client = Mock()
        mock_ssm_client = Mock()
        mock_logs_client = Mock()
        mock_s3_client = Mock()
        mock_session = Mock()

        mock_session.client.side_effect = [
            mock_ecs_client,
            mock_ssm_client,
            mock_s3_client,
            mock_logs_client,
        ]

        mock_env_obj = Mock()
        mock_env_obj.session = mock_session

        mock_application = Mock()
        mock_application.name = "myapp"
        mock_application.environments = {"dev": mock_env_obj}
        mock_load_application.return_value = mock_application

        result = CliRunner().invoke(
            internal,
            [
                "service",
                "deploy",
                "--name",
                "web",
                "--env",
                "dev",
                "--image-tag-override",
                "test123",
            ],
        )

        assert result.exit_code == 0

        mock_config_validator.assert_called_once_with()
        mock_config_provider.assert_called_once_with(mock_config_validator.return_value)
        mock_config_provider.return_value.get_enriched_config.assert_called_once_with()
        mock_load_application.assert_called_once_with(app="myapp", env="dev")

        # Check AWS clients fetched
        mock_session.client.assert_any_call("ecs")
        mock_session.client.assert_any_call("ssm")
        mock_session.client.assert_any_call("logs")
        mock_session.client.assert_any_call("s3")

        mock_ecs_provider.assert_called_once_with(
            ecs_client=mock_ecs_client,
            ssm_client=mock_ssm_client,
            application_name="myapp",
            env="dev",
        )
        mock_logs_provider.assert_called_once_with(client=mock_logs_client)
        mock_s3_provider.assert_called_once_with(client=mock_s3_client)

        mock_service_manager.assert_called_once_with(
            ecs_provider=mock_ecs_provider.return_value,
            s3_provider=mock_s3_provider.return_value,
            logs_provider=mock_logs_provider.return_value,
        )

        mock_service_manager.return_value.deploy.assert_called_once_with(
            service="web",
            environment="dev",
            application="myapp",
            image_tag_override="test123",
        )

    @patch("dbt_platform_helper.commands.internal.click.secho")
    @patch("dbt_platform_helper.commands.internal.ServiceManager")
    @patch("dbt_platform_helper.commands.internal.ECS")
    @patch("dbt_platform_helper.commands.internal.load_application")
    @patch("dbt_platform_helper.commands.internal.ConfigProvider")
    @patch("dbt_platform_helper.commands.internal.ConfigValidator")
    def test_service_deploy_exception(
        self,
        mock_config_validator,
        mock_config_provider,
        mock_load_application,
        mock_ecs,
        mock_service_manager,
        mock_click_secho,
    ):
        mock_config_provider.return_value.get_enriched_config.return_value = {
            "application": "myapp"
        }

        mock_session = Mock()
        mock_session.client.return_value = Mock()
        env = Mock(session=mock_session)
        app = Mock(name="myapp", environments={"dev": env})
        mock_load_application.return_value = app

        mock_service_manager.return_value.deploy.side_effect = PlatformException("This has failed")

        result = CliRunner().invoke(
            internal, ["service", "deploy", "--name", "web", "--env", "dev"]
        )

        assert result.exit_code == 1
        mock_click_secho.assert_called_with("Error: This has failed", err=True, fg="red")
        mock_service_manager.return_value.deploy.assert_called_once()

    @mock_aws
    @patch("dbt_platform_helper.commands.internal.ServiceManager")
    def test_generate_success(self, mock_service_manager):
        """Test that given name, environment, and image tag, the service
        generate command calls ServiceManager generate with the expected
        parameters."""

        mock_terraform_service_instance = mock_service_manager.return_value

        result = CliRunner().invoke(
            internal,
            [
                "service",
                "generate",
                "--name",
                "web",
                "--env",
                "dev",
                "--image-tag",
                "test123",
            ],
        )

        assert result.exit_code == 0

        mock_terraform_service_instance.generate.assert_called_with(
            environment="dev", services=["web"], image_tag_flag="test123"
        )

    @mock_aws
    @patch("dbt_platform_helper.commands.internal.ServiceManager")
    @patch("dbt_platform_helper.commands.internal.click.secho")
    def test_generate_catches_platform_exception_and_exits(self, mock_click, mock_service_manager):
        """Test that given incorrect arguments generate raises an exception, the
        exception is caught and the command exits."""

        mock_instance = mock_service_manager.return_value
        mock_instance.generate.side_effect = EnvironmentNotFoundException("bad env")

        result = CliRunner().invoke(
            internal,
            ["service", "generate", "--env", "bad-env"],
        )

        assert result.exit_code == 1
        mock_click.assert_called_with("Error: bad env", err=True, fg="red")
