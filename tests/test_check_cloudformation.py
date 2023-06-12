from unittest.mock import patch

from click.testing import CliRunner

import commands
from commands.check_cloudformation import check_cloudformation as check_cloudformation_command, valid_checks


class TestCheckCommand:
    def test_exit_if_no_check_specified(self):
        runner = CliRunner()

        result = runner.invoke(check_cloudformation_command)

        assert result.exit_code == 2
        assert result.output.__contains__("Error: Missing argument 'CHECK'")

    def test_exit_if_invalid_check_specified(self):
        runner = CliRunner()

        result = runner.invoke(check_cloudformation_command, ["does-not-exist"])

        assert result.exit_code == 1
        assert isinstance(result.exception, ValueError)
        assert str(result.exception).__contains__("Invalid value (does-not-exist) for 'CHECK'")

    @patch("commands.check_cloudformation.valid_checks")
    def test_runs_specific_check_when_given_check(self, valid_checks_mock):
        runner = CliRunner()

        something_else = ["all", "one"]

        valid_checks_mock.return_value = something_else

        result = runner.invoke(check_cloudformation_command, ["one"])

        assert result.exit_code == 0
        assert result.output.__contains__("Running checks: one")

    # Todo: test_runs_all_checks_when_given_all
