import re

from click.testing import CliRunner

from copilot_helper import cli


class TestCopilotHelperCli:
    def test_check_version(self):
        result = CliRunner().invoke(cli, ["--version"])

        name, version = result.output.split()

        assert result.exit_code == 0
        assert name == "dbt-copilot-tools"
        assert (re.compile(r"^\d+(\.\d+){2,}$")).match(version)
