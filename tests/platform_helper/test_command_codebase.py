import os
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_platform_helper.commands.codebase import build
from dbt_platform_helper.commands.codebase import deploy
from dbt_platform_helper.commands.codebase import list
from dbt_platform_helper.commands.codebase import prepare as prepare_command
from dbt_platform_helper.domain.codebase import NotInCodeBaseRepositoryException
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.utils.application import ApplicationNotFoundException


def mock_aws_client(get_aws_session_or_abort):
    session = MagicMock(name="session-mock")
    client = MagicMock(name="client-mock")
    session.client.return_value = client
    get_aws_session_or_abort.return_value = session

    return client


class TestCodebasePrepare:
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.codebase.ParameterStore")
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_prepare_calls_codebase_prepare_method(
        self, mock_codebase_object, mock_parameter_provider, mock_session
    ):
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client

        result = CliRunner().invoke(prepare_command)

        mock_session.return_value.client.assert_called_once_with("ssm")
        mock_parameter_provider.assert_called_with(mock_ssm_client)
        mock_codebase_object.assert_called_once_with(mock_parameter_provider.return_value)
        mock_codebase_object.return_value.prepare.assert_called_once()

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
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.codebase.ParameterStore")
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_build_calls_codebase_build_method(
        self, mock_codebase_object, mock_parameter_provider, mock_session
    ):
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client

        result = CliRunner().invoke(
            build,
            [
                "--app",
                "test-application",
                "--codebase",
                "application",
                "--commit",
                "test-commit-hash",
            ],
        )
        mock_session.return_value.client.assert_called_once_with("ssm")
        mock_parameter_provider.assert_called_with(mock_ssm_client)
        mock_codebase_object.assert_called_once_with(mock_parameter_provider.return_value)
        mock_codebase_object.return_value.build.assert_called_once()

        assert result.exit_code == 0

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


class TestCodebaseDeploy:
    @pytest.mark.parametrize(
        "flag, ref", [("--commit", "ab1c23d"), ("--tag", "1,2,3"), ("--branch", "test-branch")]
    )
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.codebase.ParameterStore")
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_deploy_successfully_triggers_a_pipeline_based_deploy(
        self, mock_codebase_object, mock_parameter_provider, mock_session, flag, ref
    ):
        mock_codebase_object_instance = mock_codebase_object.return_value

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client

        result = CliRunner().invoke(
            deploy,
            [
                "--app",
                "test-application",
                "--env",
                "development",
                "--codebase",
                "application",
                flag,
                ref,
            ],
            input="y\n",
        )

        mock_session.return_value.client.assert_called_once_with("ssm")
        mock_parameter_provider.assert_called_with(mock_ssm_client)
        mock_codebase_object.assert_called_once_with(mock_parameter_provider.return_value)

        exp_commit = ref if flag == "--commit" else None
        exp_tag = ref if flag == "--tag" else None
        exp_branch = ref if flag == "--branch" else None

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "development", "application", exp_commit, exp_tag, exp_branch
        )
        assert result.exit_code == 0

    @pytest.mark.parametrize(
        "flag, ref", [("--commit", "ab1c23d"), ("--tag", "ab1c23d"), ("--branch", "test-branch")]
    )
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.codebase.ParameterStore")
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("dbt_platform_helper.commands.codebase.ClickIOProvider")
    def test_codebase_deploy_prints_error_and_exits_when_codebase_domain_raises_platform_exception(
        self,
        mock_click,
        mock_codebase_object,
        mock_parameter_provider,
        mock_session,
        flag,
        ref,
    ):
        mock_click.return_value.abort_with_error.side_effect = SystemExit(1)
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client

        mock_codebase_object_instance = mock_codebase_object.return_value
        mock_codebase_object_instance.deploy.side_effect = PlatformException("Error message")
        result = CliRunner().invoke(
            deploy,
            [
                "--app",
                "test-application",
                "--env",
                "development",
                "--codebase",
                "application",
                flag,
                ref,
            ],
        )

        mock_session.return_value.client.assert_called_once_with("ssm")
        mock_parameter_provider.assert_called_with(mock_ssm_client)
        mock_codebase_object.assert_called_once_with(mock_parameter_provider.return_value)
        mock_codebase_object.return_value.deploy.assert_called_once()

        exp_commit = ref if flag == "--commit" else None
        exp_tag = ref if flag == "--tag" else None
        exp_branch = ref if flag == "--branch" else None

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "development", "application", exp_commit, exp_tag, exp_branch
        )
        mock_click.return_value.abort_with_error.assert_called_once_with("Error message")

        assert result.exit_code == 1


class TestCodebaseList:
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.codebase.ParameterStore")
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_lists_codebases_successfully(
        self, mock_codebase_object, mock_parameter_provider, mock_session
    ):
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client

        mock_codebase_object_instance = mock_codebase_object.return_value
        os.environ["AWS_PROFILE"] = "foo"

        result = CliRunner().invoke(list, ["--app", "test-application", "--with-images"])

        mock_session.return_value.client.assert_called_once_with("ssm")
        mock_parameter_provider.assert_called_with(mock_ssm_client)
        mock_codebase_object.assert_called_once_with(mock_parameter_provider.return_value)
        mock_codebase_object.return_value.list.assert_called_once()

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
