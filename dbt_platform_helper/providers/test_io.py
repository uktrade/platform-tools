from unittest.mock import patch

from dbt_platform_helper.providers.io import ClickIOProvider


class TestClickIOProvider:
    def test_warn_stdout(self, capsys):
        io_provider = ClickIOProvider()
        io_provider.warn("Warning!")
        captured = str(capsys.readouterr())
        assert "Warning!" in captured

    def test_error_stdout(self, capsys):
        io_provider = ClickIOProvider()
        io_provider.error("Error!")
        captured = str(capsys.readouterr())
        assert "Error!" in captured

    @patch("click.secho")
    def test_error_calls_secho_with_correct_formatting(self, mock_echo):
        io_provider = ClickIOProvider()
        io_provider.error("Error!")
        mock_echo.assert_called_once_with("Error!", fg="red")

    @patch("click.secho")
    def test_warn_calls_secho_with_correct_formatting(self, mock_echo):
        io_provider = ClickIOProvider()
        io_provider.warn("Warning!")
        mock_echo.assert_called_once_with("Warning!", fg="yellow")

    # def test_confirm(self, mock_input):
    #     mock_input.return_value="y"
    #     io_provider = IOProvider(click.secho, click.secho, click.confirm)
    #     result = io_provider.confirm("Are you sure?")
    #     assert result == True
    # assert "Are you sure?" in captured
