import re

from click.testing import CliRunner

from copilot_helper import copilot_helper


class TestCopilotHelperCli:
    def test_check_version(self):
        result = CliRunner().invoke(copilot_helper, ["--version"])

        name, version = result.output.split()

        assert result.exit_code == 0
        assert name == "dbt-copilot-tools"
        assert (re.compile(r"^\d+(\.\d+){2,}$")).match(version)

    def test_sub_commands(self):
        assert list(copilot_helper.commands.keys()) == [
            "bootstrap",
            "check-cloudformation",
            "codebuild",
            "conduit",
            "config",
            "copilot",
            "domain",
            "svc",
            "waf",
        ]
