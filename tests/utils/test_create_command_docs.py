from pathlib import Path

from click.testing import CliRunner
from pyfakefs.fake_filesystem_unittest import TestCase
from pyfakefs.fake_filesystem_unittest import patchfs

from tests.platform_helper.conftest import BASE_DIR
from tests.platform_helper.conftest import DOCS_DIR
from utils.create_command_docs import docs


class TestCreateCommandDocsCli(TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_check_required_module_option(self):
        result = self.runner.invoke(docs, ["--cmd", "bar", "--output", "baz"])

        output = result.output

        assert result.exit_code != 0
        assert "Error: Missing option '--module' / '-m'." in output

    def test_check_required_cmd_option(self):
        result = self.runner.invoke(docs, ["--module", "foo", "--output", "baz"])

        output = result.output

        assert result.exit_code != 0
        assert "Error: Missing option '--cmd' / '-c'." in output

    def test_check_required_output_option(self):
        result = self.runner.invoke(docs, ["--module", "foo", "--cmd", "bar"])

        output = result.output

        assert result.exit_code != 0
        assert "Error: Missing option '--output' / '-o'." in output

    def test_check_invalid_module_option(self):
        result = self.runner.invoke(docs, ["--module", "foo", "--cmd", "bar", "--output", "baz"])

        output = result.output

        assert result.exit_code != 0
        assert "Could not find module: foo. Error: No module named 'foo'" in output

    def test_check_invalid_cmd_option(self):
        result = self.runner.invoke(
            docs, ["--module", "platform_helper", "--cmd", "bar", "--output", "baz"]
        )

        output = result.output

        assert result.exit_code != 0
        assert "Error: Could not find command bar in platform_helper module" in output

    @patchfs
    def test_create_command_docs_template_output(self, fs):
        fs.add_real_directory(BASE_DIR / "dbt_platform_helper/templates")
        expected_output_path = "expected_output.md"
        fs.add_real_file(
            source_path=f"{DOCS_DIR}/expected_output.md", target_path=expected_output_path
        )
        expected_output = open(expected_output_path).read()
        output_path = "actual_output.md"
        assert not Path(output_path).is_file()

        result = self.runner.invoke(
            docs,
            [
                "--module",
                "tests.platform_helper.test-docs.example",
                "--cmd",
                "cli",
                "--output",
                output_path,
            ],
        )

        assert result.exit_code == 0
        assert "Markdown docs have been successfully saved to " + output_path in result.output
        assert open(output_path).read() == expected_output
