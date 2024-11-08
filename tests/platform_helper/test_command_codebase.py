import filecmp
import os
import stat
import subprocess
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import PropertyMock
from unittest.mock import patch

import boto3
import click
import pytest
import requests
from click.testing import CliRunner

from dbt_platform_helper.commands.codebase import build
from dbt_platform_helper.commands.codebase import deploy
from dbt_platform_helper.commands.codebase import list
from dbt_platform_helper.utils.application import ApplicationNotFoundError
from tests.platform_helper.conftest import EXPECTED_FILES_DIR

real_ecr_client = boto3.client("ecr")
real_ssm_client = boto3.client("ssm")


def mock_aws_client(get_aws_session_or_abort):
    session = MagicMock(name="session-mock")
    client = MagicMock(name="client-mock")
    session.client.return_value = client
    get_aws_session_or_abort.return_value = session

    return client


class TestCodebasePrepare:
    @patch("requests.get")
    def test_codebase_prepare_generates_the_expected_files(self, mocked_requests_get, tmp_path):
        from dbt_platform_helper.commands.codebase import prepare

        mocked_response_content = """
            builders:
              - name: paketobuildpacks/builder-jammy-full
                versions:
                  - version: 0.3.294
                  - version: 0.3.288
              - name: paketobuildpacks/builder-jammy-base
                versions:
                  - version: 0.1.234
                  - version: 0.5.678
              - name: paketobuildpacks/builder
                deprecated: true
                versions:
                  - version: 0.2.443-full
        """

        def mocked_response():
            r = requests.Response()
            r.status_code = 200
            type(r).content = PropertyMock(return_value=mocked_response_content.encode("utf-8"))

            return r

        mocked_requests_get.return_value = mocked_response()

        os.chdir(tmp_path)

        subprocess.run(["git", "init"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.com:uktrade/test-app.git"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        result = CliRunner().invoke(prepare)

        expected_files_dir = Path(EXPECTED_FILES_DIR) / ".copilot"
        copilot_dir = Path.cwd() / ".copilot"

        compare_directories = filecmp.dircmp(str(expected_files_dir), str(copilot_dir))

        for phase in ["build", "install", "post_build", "pre_build"]:
            assert f"phases/{phase}.sh" in result.stdout

        assert result.exit_code == 0
        assert is_same_files(compare_directories) is True

    def test_codebase_prepare_does_not_generate_files_in_the_deploy_repo(self, tmp_path):
        from dbt_platform_helper.commands.codebase import prepare

        os.chdir(tmp_path)

        subprocess.run(["git", "init"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.com:uktrade/test-app-deploy.git"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        result = CliRunner().invoke(prepare)

        assert (
            "You are in the deploy repository; make sure you are in the application codebase repository."
            in result.stdout
        )
        assert result.exit_code == 1

    def test_codebase_prepare_does_not_generate_files_in_a_repo_with_a_copilot_directory(
        self, tmp_path
    ):
        from dbt_platform_helper.commands.codebase import prepare

        os.chdir(tmp_path)
        Path(tmp_path / "copilot").mkdir()

        subprocess.run(["git", "init"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.com:uktrade/some-test-app.git"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        result = CliRunner().invoke(prepare)

        assert (
            "You are in the deploy repository; make sure you are in the application codebase repository."
            in result.stdout
        )
        assert result.exit_code == 1

    def test_codebase_prepare_generates_an_executable_image_build_run_file(self, tmp_path):
        from dbt_platform_helper.commands.codebase import prepare

        os.chdir(tmp_path)

        subprocess.run(["git", "init"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.com:uktrade/another-test-app.git"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        result = CliRunner().invoke(prepare)

        assert result.exit_code == 0
        assert stat.filemode(Path(".copilot/image_build_run.sh").stat().st_mode) == "-rwxr--r--"


@pytest.mark.focus
class TestCodebaseBuild:
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_build_does_not_trigger_build_without_an_application(
        self, mock_codebase_object
    ):

        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.build.side_effect = click.Abort
        os.environ["AWS_PROFILE"] = "foo"

        result = CliRunner().invoke(
            build,
            [
                "--app",
                "not-an-application",
                "--codebase",
                "application",
                "--commit",
                "ab1c23d",
            ],
        )

        # Assert
        mock_codebase_object_instance.build.assert_called_once_with(
            "not-an-application", "application", "ab1c23d"
        )
        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_build_aborts_with_a_nonexistent_commit_hash(self, mock_codebase_object):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.build.side_effect = SystemExit(1)
        os.environ["AWS_PROFILE"] = "foo"

        result = CliRunner().invoke(
            build,
            [
                "--app",
                "test-application",
                "--codebase",
                "application",
                "--commit",
                "nonexistent-commit-hash",
            ],
        )

        mock_codebase_object_instance.build.assert_called_once_with(
            "test-application", "application", "nonexistent-commit-hash"
        )
        assert result.exit_code == 1


class TestCodebaseDeploy:
    @pytest.mark.focus
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_deploy_successfully_triggers_a_pipeline_based_deploy(
        self, codebase_object_mock
    ):
        mock_codebase_object_instance = codebase_object_mock.return_value

        CliRunner().invoke(
            deploy,
            [
                "--app",
                "test-application",
                "--env",
                "development",
                "--codebase",
                "application",
                "--commit",
                "ab1c23d",
            ],
            input="y\n",
        )

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "development", "application", "ab1c23d"
        )

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_deploy_aborts_with_a_nonexistent_image_repository_or_image_tag(
        self, codebase_object_mock
    ):
        mock_codebase_object_instance = codebase_object_mock.return_value
        mock_codebase_object_instance.deploy.side_effect = click.Abort

        result = CliRunner().invoke(
            deploy,
            [
                "--app",
                "test-application",
                "--env",
                "development",
                "--codebase",
                "application",
                "--commit",
                "nonexistent-commit-hash",
            ],
        )

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "development", "application", "nonexistent-commit-hash"
        )
        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_deploy_does_not_trigger_build_without_an_application(
        self, mock_codebase_object
    ):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.deploy.side_effect = click.Abort
        os.environ["AWS_PROFILE"] = "foo"

        result = CliRunner().invoke(
            deploy,
            [
                "--app",
                "not-an-application",
                "--env",
                "dev",
                "--codebase",
                "application",
                "--commit",
                "ab1c23d",
            ],
        )

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "not-an-application", "dev", "application", "ab1c23d"
        )
        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_deploy_does_not_trigger_build_with_missing_environment(
        self, mock_codebase_object
    ):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.deploy.side_effect = click.Abort
        os.environ["AWS_PROFILE"] = "foo"

        result = CliRunner().invoke(
            deploy,
            [
                "--app",
                "test-application",
                "--env",
                "not-an-environment",
                "--codebase",
                "application",
                "--commit",
                "ab1c23d",
            ],
        )

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "not-an-environment", "application", "ab1c23d"
        )
        assert result.exit_code == 1


class TestCodebaseList:
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_lists_codebases_successfully(self, mock_codebase_object):
        mock_codebase_object_instance = mock_codebase_object.return_value
        os.environ["AWS_PROFILE"] = "foo"

        result = CliRunner().invoke(list, ["--app", "test-application", "--with-images"])

        mock_codebase_object_instance.list.assert_called_once_with("test-application", True)
        assert result.exit_code == 0

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_aborts_when_application_has_no_codebases(self, mock_codebase_object):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.list.side_effect = SystemExit(1)
        os.environ["AWS_PROFILE"] = "foo"

        result = CliRunner().invoke(list, ["--app", "test-application", "--with-images"])

        mock_codebase_object_instance.list.assert_called_once_with("test-application", True)
        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_aborts_when_application_does_not_exist(self, mock_codebase_object):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.list.side_effect = ApplicationNotFoundError
        os.environ["AWS_PROFILE"] = "foo"

        result = CliRunner().invoke(list, ["--app", "test-application", "--with-images"])

        mock_codebase_object_instance.list.assert_called_once_with("test-application", True)
        assert result.exit_code == 1


def is_same_files(compare_directories):
    """
    Recursively compare two directories to check if the files are the same or
    not.

    Returns True or False.
    """
    if (
        compare_directories.diff_files
        or compare_directories.left_only
        or compare_directories.right_only
    ):
        for name in compare_directories.diff_files:
            print(
                "diff_file %s found in %s and %s"
                % (name, compare_directories.left, compare_directories.right)
            )

        return False

    for sub_compare_directories in compare_directories.subdirs.values():
        if not is_same_files(sub_compare_directories):
            return False

    return True
