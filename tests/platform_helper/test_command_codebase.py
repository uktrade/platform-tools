import os
from unittest.mock import MagicMock
from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.codebase import build
from dbt_platform_helper.commands.codebase import deploy
from dbt_platform_helper.commands.codebase import list
from dbt_platform_helper.commands.codebase import prepare as prepare_command
from dbt_platform_helper.exceptions import ApplicationEnvironmentNotFoundError
from dbt_platform_helper.exceptions import ApplicationNotFoundError
from dbt_platform_helper.exceptions import CopilotCodebaseNotFoundError
from dbt_platform_helper.exceptions import ImageNotFoundError
from dbt_platform_helper.exceptions import NoCopilotCodebasesFoundError
from dbt_platform_helper.exceptions import NotInCodeBaseRepositoryError
from dbt_platform_helper.utils.git import CommitNotFoundError


def mock_aws_client(get_aws_session_or_abort):
    session = MagicMock(name="session-mock")
    client = MagicMock(name="client-mock")
    session.client.return_value = client
    get_aws_session_or_abort.return_value = session

    return client


class TestCodebasePrepare:
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_prepare_calls_codebase_prepare_method(self, mock_codebase_object):
        mock_codebase_object_instance = mock_codebase_object.return_value

        result = CliRunner().invoke(prepare_command)
        print(result.output)
        mock_codebase_object_instance.prepare.assert_called_once()

        assert result.exit_code == 0

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_aborts_when_not_in_a_codebase_repository(self, mock_click, mock_codebase_object):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.prepare.side_effect = NotInCodeBaseRepositoryError
        os.environ["AWS_PROFILE"] = "foo"

        result = CliRunner().invoke(prepare_command)

        expected_message = "You are in the deploy repository; make sure you are in the application codebase repository."
        mock_click.assert_called_with(expected_message, fg="red")
        assert result.exit_code == 1


class TestCodebaseBuild:
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_build_does_not_trigger_build_without_an_application(
        self, mock_click, mock_codebase_object
    ):

        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.build.side_effect = ApplicationNotFoundError
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
        expected_message = f"""The account "foo" does not contain the application "not-an-application"; ensure you have set the environment variable "AWS_PROFILE" correctly."""
        mock_click.assert_called_with(expected_message, fg="red")

        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_build_aborts_with_a_nonexistent_commit_hash(
        self, mock_click, mock_codebase_object
    ):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.build.side_effect = CommitNotFoundError()
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
        expected_message = f"""The commit hash "nonexistent-commit-hash" either does not exist or you need to run `git fetch`."""
        mock_click.assert_called_with(expected_message, fg="red")
        assert result.exit_code == 1


class TestCodebaseDeploy:
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
    @patch("click.secho")
    def test_codebase_deploy_aborts_with_a_nonexistent_image_repository_or_image_tag(
        self, mock_click, codebase_object_mock
    ):
        mock_codebase_object_instance = codebase_object_mock.return_value
        mock_codebase_object_instance.deploy.side_effect = ImageNotFoundError
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
        expected_message = f"""The commit hash "nonexistent-commit-hash" has not been built into an image, try the `platform-helper codebase build` command first."""
        mock_click.assert_called_with(expected_message, fg="red")
        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_deploy_does_not_trigger_build_without_an_application(
        self, mock_click, mock_codebase_object
    ):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.deploy.side_effect = ApplicationNotFoundError
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
        expected_message = f"""The account "foo" does not contain the application "not-an-application"; ensure you have set the environment variable "AWS_PROFILE" correctly."""
        mock_click.assert_called_with(expected_message, fg="red")
        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_deploy_does_not_trigger_build_with_missing_environment(
        self, mock_click, mock_codebase_object
    ):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.deploy.side_effect = ApplicationEnvironmentNotFoundError
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
        expected_message = f"""The environment "not-an-environment" either does not exist or has not been deployed."""
        mock_click.assert_called_with(expected_message, fg="red")
        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_deploy_does_not_trigger_build_with_missing_codebase(
        self, mock_click, mock_codebase_object
    ):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.deploy.side_effect = CopilotCodebaseNotFoundError
        os.environ["AWS_PROFILE"] = "foo"

        result = CliRunner().invoke(
            deploy,
            [
                "--app",
                "test-application",
                "--env",
                "test-environment",
                "--codebase",
                "not-a-codebase",
                "--commit",
                "ab1c23d",
            ],
        )

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "test-environment", "not-a-codebase", "ab1c23d"
        )
        expected_message = (
            f"""The codebase "not-a-codebase" either does not exist or has not been deployed."""
        )
        mock_click.assert_called_with(expected_message, fg="red")
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
    @patch("click.secho")
    def test_list_aborts_when_application_has_no_codebases(self, mock_click, mock_codebase_object):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.list.side_effect = NoCopilotCodebasesFoundError
        os.environ["AWS_PROFILE"] = "foo"

        result = CliRunner().invoke(list, ["--app", "test-application", "--with-images"])

        expected_message = f"""No codebases found for application "test-application"""
        mock_click.assert_called_with(expected_message, fg="red")
        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_aborts_when_application_does_not_exist(self, mock_click, mock_codebase_object):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.list.side_effect = ApplicationNotFoundError
        os.environ["AWS_PROFILE"] = "foo"

        result = CliRunner().invoke(list, ["--app", "test-application", "--with-images"])

        app = "test-application"
        expected_message = f"""The account "{os.environ.get("AWS_PROFILE")}" does not contain the application "{app}"; ensure you have set the environment variable "AWS_PROFILE" correctly."""
        mock_click.assert_called_with(expected_message, fg="red")
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
