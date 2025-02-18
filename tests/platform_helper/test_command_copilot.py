from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.copilot import make_addons


class TestMakeAddonsCommand:
    @patch("dbt_platform_helper.commands.copilot.Copilot.make_addons")
    @patch("click.secho")
    def test_calls_make_addons(
        self,
        mock_click,
        mock_make_addons,
    ):
        mock_make_addons.return_value = None

        result = CliRunner().invoke(make_addons, [])

        assert result.exit_code == 0
        mock_make_addons.assert_called_with()

    @patch("dbt_platform_helper.commands.copilot.Copilot.make_addons")
    @patch("click.secho")
    def test_prints_error_message_if_exception_is_thrown_by_make_addons(
        self,
        mock_click,
        mock_make_addons,
    ):
        mock_make_addons.side_effect = Exception("Something bad happened")

        result = CliRunner().invoke(make_addons, [])

        assert result.exit_code == 1
        mock_click.assert_called_with("Error: Something bad happened", err=True, fg="red")
