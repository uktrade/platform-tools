import os
from unittest import TestCase

from click.testing import CliRunner

from tests.conftest import BASE_DIR
from utils.create_command_docs import docs


class TestCreateCommandDocsCli(TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    @classmethod
    def tearDownClass(cls):
        os.remove(f"{BASE_DIR}/tests/docs/docs.md")
        os.remove(f"{BASE_DIR}/tests/docs/example.md")

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
        result = self.runner.invoke(docs, ["--module", "copilot_helper", "--cmd", "bar", "--output", "baz"])

        output = result.output

        assert result.exit_code != 0
        assert "Error: Could not find command bar in copilot_helper module" in output

    def test_create_command_docs(self):
        output_path = f"{BASE_DIR}/tests/docs/docs.md"

        assert os.path.exists(output_path) is False

        result = self.runner.invoke(
            docs,
            [
                "--module",
                "copilot_helper",
                "--cmd",
                "copilot_helper",
                "--output",
                output_path,
            ],
        )

        output = result.output

        assert result.exit_code == 0
        assert "Markdown docs have been successfully saved to " + output_path in output

    def test_create_command_docs_template_output(self):
        output_path = f"{BASE_DIR}/tests/docs/example.md"
        expected_output_path = f"{BASE_DIR}/tests/docs/expected_output.md"

        assert os.path.exists(output_path) is False

        self.runner.invoke(
            docs,
            [
                "--module",
                "tests.docs.example",
                "--cmd",
                "cli",
                "--output",
                output_path,
            ],
        )

        output = open(output_path).read()
        expected_output = open(expected_output_path).read()

        assert output == expected_output
