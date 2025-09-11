from unittest.mock import Mock
from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.internal import internal
from dbt_platform_helper.platform_exception import PlatformException


class TestInternal:
    @patch("dbt_platform_helper.commands.internal.Internal")
    @patch("dbt_platform_helper.commands.internal.ECS")
    @patch("dbt_platform_helper.commands.internal.load_application")
    @patch("dbt_platform_helper.commands.internal.ConfigProvider")
    @patch("dbt_platform_helper.commands.internal.ConfigValidator")
    def test_service_deploy_success(
        self,
        mock_config_validator,
        mock_config_provider,
        mock_load_application,
        mock_ecs,
        mock_internal,
    ):

        mock_config_provider.return_value.get_enriched_config.return_value = {
            "application": "myapp"
        }

        # Mock AWS calls
        mock_ecs_client = Mock()
        mock_ssm_client = Mock()
        mock_session = Mock()

        mock_session.client.side_effect = [mock_ecs_client, mock_ssm_client]

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
                "--environment",
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

        mock_ecs.assert_called_once_with(mock_ecs_client, mock_ssm_client, "myapp", "dev")

        mock_internal.assert_called_once_with(ecs_provider=mock_ecs.return_value)
        mock_internal.return_value.deploy.assert_called_once_with(
            service="web",
            environment="dev",
            application="myapp",
            image_tag_override="test123",
        )

    @patch("dbt_platform_helper.commands.internal.click.secho")
    @patch("dbt_platform_helper.commands.internal.Internal")
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
        mock_internal,
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

        mock_internal.return_value.deploy.side_effect = PlatformException("This has failed")

        result = CliRunner().invoke(
            internal, ["service", "deploy", "--name", "web", "--environment", "dev"]
        )

        assert result.exit_code == 1
        mock_click_secho.assert_called_with("Error: This has failed", err=True, fg="red")
        mock_internal.return_value.deploy.assert_called_once()
