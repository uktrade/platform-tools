import re

from click.testing import CliRunner


class TestCopilotHelperCli:
    def test_check_version(self):
        from platform_helper import platform_helper

        result = CliRunner().invoke(platform_helper, ["--version"])

        name, version = result.output.split()

        assert result.exit_code == 0
        assert name == "dbt-platform-helper"
        assert (re.compile(r"^\d+(\.\d+){2,}$")).match(version)

    def test_sub_commands(self):
        from platform_helper import platform_helper

        assert list(platform_helper.commands.keys()) == [
            # "bootstrap",
            "check-cloudformation",
            "codebase",
            "conduit",
            "config",
            "copilot",
            "domain",
            "cdn",
            "environment",
            "generate",
            "pipeline",
            "application",
        ]
