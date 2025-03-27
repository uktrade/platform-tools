from unittest.mock import MagicMock
from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.copilot import make_addons


class TestMakeAddonsCommand:
    @patch("dbt_platform_helper.commands.copilot.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.copilot.KMSProvider")
    @patch("dbt_platform_helper.commands.copilot.Copilot")
    @patch("dbt_platform_helper.commands.copilot.ConfigProvider")
    @patch("dbt_platform_helper.commands.copilot.ParameterStore")
    @patch("dbt_platform_helper.commands.copilot.ConfigValidator")
    @patch("dbt_platform_helper.commands.copilot.FileProvider")
    @patch("dbt_platform_helper.commands.copilot.CopilotTemplating")
    def test_calls_make_addons(
        self,
        mock_copilot_templating,
        mock_file_provider,
        mock_config_validator,
        mock_parameter_store,
        mock_config_provider,
        mock_copilot,
        mock_kms_provider,
        mock_get_aws_session_or_abort,
    ):

        mock_session = MagicMock()
        mock_get_aws_session_or_abort.return_value = mock_session
        mock_copilot_instance = mock_copilot.return_value

        result = CliRunner().invoke(make_addons, [])

        mock_get_aws_session_or_abort.assert_called_once()
        mock_config_validator.assert_called_once()
        mock_config_provider.assert_called_once_with(mock_config_validator.return_value)

        assert result.exit_code == 0
        mock_copilot.assert_called_once_with(
            mock_config_provider.return_value,
            mock_parameter_store.return_value,
            mock_file_provider.return_value,
            mock_copilot_templating.return_value,
            mock_kms_provider,
            mock_session,
        )
        mock_copilot_instance.make_addons.assert_called_once()

    @patch("dbt_platform_helper.commands.copilot.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.copilot.KMSProvider")
    @patch("dbt_platform_helper.commands.copilot.Copilot")
    @patch("dbt_platform_helper.commands.copilot.ConfigProvider")
    @patch("dbt_platform_helper.commands.copilot.ParameterStore")
    @patch("dbt_platform_helper.commands.copilot.ConfigValidator")
    @patch("dbt_platform_helper.commands.copilot.FileProvider")
    @patch("dbt_platform_helper.commands.copilot.CopilotTemplating")
    @patch("click.secho")
    def test_prints_error_message_if_exception_is_thrown_by_make_addons(
        self,
        mock_click,
        mock_copilot_templating,
        mock_file_provider,
        mock_config_validator,
        mock_parameter_store,
        mock_config_provider,
        mock_copilot,
        mock_kms_provider,
        mock_get_aws_session_or_abort,
    ):
        mock_session = MagicMock()
        mock_get_aws_session_or_abort.return_value = mock_session
        mock_copilot_instance = mock_copilot.return_value
        mock_copilot_instance.make_addons.side_effect = Exception("Something bad happened")

        result = CliRunner().invoke(make_addons, [])

        mock_get_aws_session_or_abort.assert_called_once()
        mock_config_validator.assert_called_once()
        mock_config_provider.assert_called_once_with(mock_config_validator.return_value)

        assert result.exit_code == 1
        mock_copilot.assert_called_with(
            mock_config_provider.return_value,
            mock_parameter_store.return_value,
            mock_file_provider.return_value,
            mock_copilot_templating.return_value,
            mock_kms_provider,
            mock_session,
        )
        mock_copilot_instance.make_addons.assert_called_once()
        mock_click.assert_called_with("Error: Something bad happened", err=True, fg="red")
