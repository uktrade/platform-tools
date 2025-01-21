from unittest.mock import patch

from dbt_platform_helper.providers.io import ClickIOProvider


class TestClickIOProvider:
    def test_warn_stdout(self, capsys):
        io = ClickIOProvider()
        io.warn("Warning!")
        captured = str(capsys.readouterr())
        assert "Warning!" in captured

    def test_error_stdout(self, capsys):
        io = ClickIOProvider()
        io.error("Error!")
        captured = str(capsys.readouterr())
        assert "Error!" in captured

    @patch("click.secho")
    def test_error_calls_secho_with_correct_formatting(self, mock_echo):
        io = ClickIOProvider()
        io.error("Error!")
        mock_echo.assert_called_once_with("Error!", fg="red")

    @patch("click.secho")
    def test_warn_calls_secho_with_correct_formatting(self, mock_echo):
        io = ClickIOProvider()
        io.warn("Warning!")
        mock_echo.assert_called_once_with("Warning!", fg="yellow")

    @patch("click.confirm")
    def test_confirm(self, mock_confirm):
        io = ClickIOProvider()
        io.confirm("Are you sure?")
        mock_confirm.assert_called_once_with("Are you sure?")
