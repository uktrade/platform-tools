import os
from unittest.mock import MagicMock
from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.codebase import build
from dbt_platform_helper.commands.codebase import deploy
from dbt_platform_helper.commands.codebase import list
from dbt_platform_helper.commands.codebase import prepare as prepare_command
from dbt_platform_helper.domain.codebase import ApplicationEnvironmentNotFoundException
from dbt_platform_helper.domain.codebase import NotInCodeBaseRepositoryException
from dbt_platform_helper.providers.aws.exceptions import (
    CopilotCodebaseNotFoundException,
)
from dbt_platform_helper.providers.aws.exceptions import ImageNotFoundException
from dbt_platform_helper.utils.application import ApplicationNotFoundException
from dbt_platform_helper.utils.git import CommitNotFoundException


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
        mock_codebase_object_instance.prepare.assert_called_once()

        assert result.exit_code == 0

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_aborts_when_not_in_a_codebase_repository(self, mock_click, mock_codebase_object):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.prepare.side_effect = NotInCodeBaseRepositoryException
        os.environ["AWS_PROFILE"] = "foo"

        result = CliRunner().invoke(prepare_command)

        assert result.exit_code == 1


class TestCodebaseBuild:
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_build_does_not_trigger_build_without_an_application(
        self, mock_click, mock_codebase_object
    ):

        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.build.side_effect = ApplicationNotFoundException
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

        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_build_aborts_with_a_nonexistent_commit_hash(
        self, mock_click, mock_codebase_object
    ):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.build.side_effect = CommitNotFoundException()
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
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_deploy_successfully_triggers_a_pipeline_based_deploy(
        self, codebase_object_mock
    ):
        mock_codebase_object_instance = codebase_object_mock.return_value

        result = CliRunner().invoke(
            deploy,
            [
                "--app",
                "test-application",
                "--env",
                "development",
                "--codebase",
                "application",
                "--ref",
                "ab1c23d",
            ],
            input="y\n",
        )

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "development", "application", None, "ab1c23d"
        )
        assert result.exit_code == 0

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_deploy_warning_when_using_commit(self, codebase_object_mock):
        mock_codebase_object_instance = codebase_object_mock.return_value

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
                "ab1c23d",
            ],
            input="y\n",
        )

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "development", "application", "ab1c23d", None
        )

        assert (
            result.stdout
            == "WARNING: The --commit option is deprecated and will be removed in a future release. Use --ref instead to pass the ECR image tag, GitHub commit hash, or branch name.\n"
        )
        assert result.exit_code == 0

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_deploy_aborts_with_no_commit_or_ref(self, codebase_object_mock):

        result = CliRunner().invoke(
            deploy,
            ["--app", "test-application", "--env", "development", "--codebase", "application"],
        )

        assert result.stdout == "Error: You must provide either --commit OR --ref, but not both.\n"
        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_deploy_aborts_with_both_commit_and_ref(self, codebase_object_mock):

        result = CliRunner().invoke(
            deploy,
            [
                "--app",
                "test-application",
                "--env",
                "development",
                "--codebase",
                "application",
                "--ref",
                "test-ref-1234",
                "--commit",
                "test-commit-1234",
            ],
        )

        deprecated_msg = "WARNING: The --commit option is deprecated and will be removed in a future release. Use --ref instead to pass the ECR image tag, GitHub commit hash, or branch name.\n"
        error_msg = "Error: You must provide either --commit OR --ref, but not both.\n"
        assert (deprecated_msg and error_msg) in result.stdout
        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_deploy_aborts_with_a_nonexistent_image_repository_or_ref(
        self, mock_click, codebase_object_mock
    ):
        mock_codebase_object_instance = codebase_object_mock.return_value
        mock_codebase_object_instance.deploy.side_effect = ImageNotFoundException
        result = CliRunner().invoke(
            deploy,
            [
                "--app",
                "test-application",
                "--env",
                "development",
                "--codebase",
                "application",
                "--ref",
                "nonexistent-ref",
            ],
        )

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "development", "application", None, "nonexistent-ref"
        )
        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_deploy_does_not_trigger_build_without_an_application(
        self, mock_click, mock_codebase_object
    ):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.deploy.side_effect = ApplicationNotFoundException
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
                "--ref",
                "ab1c23d",
            ],
        )

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "not-an-application", "dev", "application", None, "ab1c23d"
        )
        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_deploy_does_not_trigger_build_with_missing_environment(
        self, mock_click, mock_codebase_object
    ):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.deploy.side_effect = ApplicationEnvironmentNotFoundException
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
                "--ref",
                "ab1c23d",
            ],
        )

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "not-an-environment", "application", None, "ab1c23d"
        )
        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_deploy_does_not_trigger_build_with_missing_codebase(
        self, mock_click, mock_codebase_object
    ):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.deploy.side_effect = CopilotCodebaseNotFoundException
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
                "--ref",
                "ab1c23d",
            ],
        )

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "test-environment", "not-a-codebase", None, "ab1c23d"
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
    @patch("click.secho")
    def test_aborts_when_application_does_not_exist(self, mock_click, mock_codebase_object):
        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.list.side_effect = ApplicationNotFoundException
        os.environ["AWS_PROFILE"] = "foo"

        result = CliRunner().invoke(list, ["--app", "test-application", "--with-images"])

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
