import pytest
from click.testing import CliRunner

from commands.check_cloudformation import check_cloudformation as check_cloudformation_command


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
