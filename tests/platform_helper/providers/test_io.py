from io import StringIO
from unittest.mock import call
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
            result = ClickIOProvider().input("Please enter a service")
            assert result == "web"

    def test_abort_with_error(self, capsys):
        io = ClickIOProvider()
        with pytest.raises(SystemExit):
            io.abort_with_error("Error!")
        assert "Error!" in str(capsys.readouterr())

    @pytest.mark.parametrize(
        "input, expected",
        [
            ("y", True),
            ("n", False),
            ("yes", True),
            ("no", False),
            ("   Y   ", True),
        ],
    )
    def test_confirm_with_various_valid_user_input(self, input, expected):
        mock_input = StringIO(input)
        with patch("sys.stdin", mock_input):
            result = ClickIOProvider().confirm("Is that really your name?")
            assert result == expected

    def test_confirm_throws_abort_error_when_invalid_input(self):
        mock_input = StringIO("maybe")
        with patch("sys.stdin", mock_input):
            with pytest.raises(ClickIOProviderException) as e:
                ClickIOProvider().confirm("Is that really your name?")
            assert str(e.value) == "Is that really your name? [y/N]: Error: invalid input"

    @patch("click.secho")
    def test_warn_calls_secho_with_correct_formatting(self, mock_echo):
        io = ClickIOProvider()
        io.warn("Warning!")
        mock_echo.assert_called_once_with("Warning!", fg="magenta")

    @patch("click.secho")
    def test_error_calls_secho_with_correct_formatting(self, mock_echo):
        io = ClickIOProvider()
        io.error("Error!")
        mock_echo.assert_called_once_with("Error: Error!", fg="red")

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

    @patch("click.secho")
    def test_info_calls_secho_with_correct_formatting(self, mock_echo):
        io = ClickIOProvider()
        with pytest.raises(SystemExit):
            io.abort_with_error("Aborting")
        mock_echo.assert_called_once_with("Error: Aborting", err=True, fg="red")


class TestClickIOProviderProcessMessages:
    @patch("click.secho")
    def test_with_empty_messages(self, mock_echo):
        io = ClickIOProvider()
        messages = {"errors": [], "warnings": [], "info": []}
        io.process_messages(messages)
        mock_echo.assert_not_called()

    @patch("click.secho")
    def test_with_none_messages(self, mock_echo):
        io = ClickIOProvider()
        messages = {"errors": [], "warnings": [], "info": []}
        io.process_messages(None)
        mock_echo.assert_not_called()

    @patch("click.secho")
    def test_echos_populated_messages_with_correct_formatting(self, mock_echo):
        io = ClickIOProvider()
        messages = {
            "errors": ["error_1", "error_2"],
            "warnings": ["warning_1", "warning_2"],
            "info": ["info_1", "info_2"],
        }
        io.process_messages(messages)
        mock_echo.assert_has_calls(
            [
                call("Error: error_1\nerror_2", fg="red"),
                call("warning_1\nwarning_2", fg="magenta"),
                call("info_1\ninfo_2"),
            ]
        )
