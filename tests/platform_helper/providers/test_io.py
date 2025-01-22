from io import StringIO
from unittest.mock import patch

import pytest

from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.io import ClickIOProviderException


class TestClickIOProvider:
    def test_warn_stdout(self, capsys):
        io = ClickIOProvider()
        io.warn("Warning!")
        assert "Warning!" in str(capsys.readouterr())

    def test_error_stdout(self, capsys):
        io = ClickIOProvider()
        io.error("Error!")
        assert "Error!" in str(capsys.readouterr())

    def test_info_stdout(self, capsys):
        io = ClickIOProvider()
        io.info("Info.")
        assert "Info." in str(capsys.readouterr())

    def test_input(self):
        mock_input = StringIO("web")
        with patch("sys.stdin", mock_input):
            result = ClickIOProvider.input("Please select a service")
            assert result == "web"

    @pytest.mark.parametrize(
        "input, expected",
        [
            ("y", True),
            ("n", False),
            ("yes", True),
            ("no", False),
        ],
    )
    def test_confirm_with_various_valid_user_input(self, input, expected):
        mock_input = StringIO(input)
        with patch("sys.stdin", mock_input):
            result = ClickIOProvider.confirm("Is that really your name?")
            assert result == expected

    def test_confirm_throws_abort_error_when_invalid_input(self):
        mock_input = StringIO("maybe")
        with patch("sys.stdin", mock_input):
            with pytest.raises(ClickIOProviderException) as e:
                ClickIOProvider.confirm("Is that really your name?")
            assert str(e.value) == "Is that really your name? [y/N]: Error: invalid input"

    @patch("click.secho")
    def test_warn_calls_secho_with_correct_formatting(self, mock_echo):
        io = ClickIOProvider()
        io.warn("Warning!")
        mock_echo.assert_called_once_with("Warning!", fg="yellow")

    @patch("click.secho")
    def test_error_calls_secho_with_correct_formatting(self, mock_echo):
        io = ClickIOProvider()
        io.error("Error!")
        mock_echo.assert_called_once_with("Error!", fg="red")

    @patch("click.secho")
    def test_info_calls_secho_with_correct_formatting(self, mock_echo):
        io = ClickIOProvider()
        io.info("Info.")
        mock_echo.assert_called_once_with("Info.")

    @patch("click.prompt")
    def test_input(self, mock_prompt):
        io = ClickIOProvider()
        io.input("Please select a service")
        mock_prompt.assert_called_once_with("Please select a service")

    @patch("click.confirm")
    def test_confirm(self, mock_confirm):
        io = ClickIOProvider()
        io.confirm("Are you sure?")
        mock_confirm.assert_called_once_with("Are you sure?")
