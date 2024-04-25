from pathlib import Path
from unittest import TestCase

from click.testing import CliRunner

# from pyfakefs.fake_filesystem_unittest import TestCase
from pyfakefs.fake_filesystem_unittest import TestCase
from pyfakefs.fake_filesystem_unittest import patchfs

from tests.platform_helper.conftest import BASE_DIR
from tests.platform_helper.conftest import DOCS_DIR
from utils.create_command_docs import docs

# @pytest.fixture
# def mock_create_docs(monkeypatch):
#     def mock_create_docs_func(base_command, output):
#         output = f"{DOCS_DIR}/example.md"
#         create_docs(base_command, output)
#
#     monkeypatch.setattr("utils.create_command_docs.create_docs", mock_create_docs_func)


class TestCreateCommandDocsCli(TestCase):
    def setUp(self) -> None:
        self.setUpPyfakefs()
        self.runner = CliRunner()

    @classmethod
    def tearDownClass(cls):
        Path(f"{DOCS_DIR}/test-docs.md").unlink(missing_ok=True)
        Path(f"{DOCS_DIR}/example.md").unlink(missing_ok=True)

    # def teardown(self) -> None:
    #     # self._cleanup()
    #     pass
    #
    # def _cleanup(self):
    #     Path(f"{DOCS_DIR}/test-docs.md").unlink(missing_ok=True)
    #     Path(f"{DOCS_DIR}/example.md").unlink(missing_ok=True)

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

    def test_create_command_docs(self):
        output_path = f"{DOCS_DIR}/test-docs.md"

        assert not Path(output_path).is_file()

        result = self.runner.invoke(
            docs,
            [
                "--module",
                "platform_helper",
                "--cmd",
                "platform_helper",
                "--output",
                output_path,
            ],
        )

        output = result.output

        assert result.exit_code == 0
        assert "Markdown docs have been successfully saved to " + output_path in output

    # @pytest.mark.usefixtures("mock_create_docs")
    @patchfs
    def test_create_command_docs_template_output(self, fs):
        output_path = f"{DOCS_DIR}/example.md"
        expected_output_path = f"{DOCS_DIR}/expected_output.md"

        fs.add_real_directory(BASE_DIR / "dbt_platform_helper/templates", lazy_read=True)

        assert not Path(output_path).is_file()

        self.runner.invoke(
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
        print(f"LOOK HERE: {open(output_path).read()}")
        output = open(output_path).read()
        expected_output = open(expected_output_path).read()

        assert output == expected_output
