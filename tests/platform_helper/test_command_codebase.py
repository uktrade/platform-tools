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

    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.codebase.ParameterStore")
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_build_aborts_with_a_nonexistent_commit_hash(
        self, mock_click, mock_codebase_object, mock_parameter_provider, mock_session
    ):
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client

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

        mock_session.return_value.client.assert_called_once_with("ssm")
        mock_parameter_provider.assert_called_with(mock_ssm_client)
        mock_codebase_object.assert_called_once_with(mock_parameter_provider.return_value)
        mock_codebase_object.return_value.build.assert_called_once()

        mock_codebase_object_instance.build.assert_called_once_with(
            "test-application", "application", "nonexistent-commit-hash"
        )

        assert result.exit_code == 1


class TestCodebaseDeploy:
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.codebase.ParameterStore")
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_prepare_calls_codebase_prepare_method(
        self, mock_codebase_object, mock_parameter_provider, mock_session
    ):
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
                "--commit",
                "ab1c23d",
            ],
        )
        mock_session.return_value.client.assert_called_once_with("ssm")
        mock_parameter_provider.assert_called_with(mock_ssm_client)
        mock_codebase_object.assert_called_once_with(mock_parameter_provider.return_value)
        mock_codebase_object.return_value.deploy.assert_called_once()

        assert result.exit_code == 0

    @pytest.mark.parametrize(
        "flag, commit, ref", [("--commit", "ab1c23d", None), ("--ref", None, "ab1c23d")]
    )
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.codebase.ParameterStore")
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_deploy_successfully_triggers_a_pipeline_based_deploy(
        self, mock_codebase_object, mock_parameter_provider, mock_session, flag, commit, ref
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
                commit if commit else ref,
            ],
            input="y\n",
        )

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "development", "application", commit, ref
        )
        assert result.exit_code == 0

    @pytest.mark.parametrize(
        "flag, commit, ref", [("--commit", "ab1c23d", None), ("--ref", None, "ab1c23d")]
    )
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.codebase.ParameterStore")
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_deploy_aborts_with_a_nonexistent_image_repository_or_ref(
        self,
        mock_click,
        mock_codebase_object,
        mock_parameter_provider,
        mock_session,
        flag,
        commit,
        ref,
    ):

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client

        mock_codebase_object_instance = mock_codebase_object.return_value
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
                flag,
                commit if commit else ref,
            ],
        )

        mock_session.return_value.client.assert_called_once_with("ssm")
        mock_parameter_provider.assert_called_with(mock_ssm_client)
        mock_codebase_object.assert_called_once_with(mock_parameter_provider.return_value)
        mock_codebase_object.return_value.deploy.assert_called_once()

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "development", "application", commit, ref
        )
        assert result.exit_code == 1

    @pytest.mark.parametrize(
        "flag, commit, ref", [("--commit", "ab1c23d", None), ("--ref", None, "commit-ab1c23d")]
    )
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.codebase.ParameterStore")
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_deploy_does_not_trigger_build_without_an_application(
        self,
        mock_click,
        mock_codebase_object,
        mock_parameter_provider,
        mock_session,
        flag,
        commit,
        ref,
    ):

        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client

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
                flag,
                commit if commit else ref,
            ],
        )

        mock_session.return_value.client.assert_called_once_with("ssm")
        mock_parameter_provider.assert_called_with(mock_ssm_client)
        mock_codebase_object.assert_called_once_with(mock_parameter_provider.return_value)
        mock_codebase_object.return_value.deploy.assert_called_once()

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "not-an-application", "dev", "application", commit, ref
        )
        assert result.exit_code == 1

    @pytest.mark.parametrize(
        "flag, commit, ref", [("--commit", "ab1c23d", None), ("--ref", None, "ab1c23d")]
    )
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.codebase.ParameterStore")
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_deploy_does_not_trigger_build_with_missing_environment(
        self,
        mock_click,
        mock_codebase_object,
        mock_parameter_provider,
        mock_session,
        flag,
        commit,
        ref,
    ):
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client

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
                flag,
                commit if commit else ref,
            ],
        )

        mock_session.return_value.client.assert_called_once_with("ssm")
        mock_parameter_provider.assert_called_with(mock_ssm_client)
        mock_codebase_object.assert_called_once_with(mock_parameter_provider.return_value)
        mock_codebase_object.return_value.deploy.assert_called_once()

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "not-an-environment", "application", commit, ref
        )
        assert result.exit_code == 1

    @pytest.mark.parametrize(
        "flag, commit, ref", [("--commit", "ab1c23d", None), ("--ref", None, "ab1c23d")]
    )
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.codebase.ParameterStore")
    @patch("dbt_platform_helper.commands.codebase.Codebase")
    @patch("click.secho")
    def test_codebase_deploy_does_not_trigger_build_with_missing_codebase(
        self,
        mock_click,
        mock_codebase_object,
        mock_parameter_provider,
        mock_session,
        flag,
        commit,
        ref,
    ):
        mock_ssm_client = Mock()
        mock_session.return_value.client.return_value = mock_ssm_client

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
                flag,
                commit if commit else ref,
            ],
        )

        mock_session.return_value.client.assert_called_once_with("ssm")
        mock_parameter_provider.assert_called_with(mock_ssm_client)
        mock_codebase_object.assert_called_once_with(mock_parameter_provider.return_value)
        mock_codebase_object.return_value.deploy.assert_called_once()

        mock_codebase_object_instance.deploy.assert_called_once_with(
            "test-application", "test-environment", "not-a-codebase", commit, ref
        )
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
