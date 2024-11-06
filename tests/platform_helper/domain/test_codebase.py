import json
from unittest import mock
from unittest.mock import MagicMock, Mock, call, patch

import click
import pytest

from dbt_platform_helper.domain.codebase import Codebase
from dbt_platform_helper.utils.application import Application, ApplicationNotFoundError, Environment


def mock_aws_client(get_aws_session_or_abort):
    session = MagicMock(name="session-mock")
    client = MagicMock(name="client-mock")
    session.client.return_value = client
    get_aws_session_or_abort.return_value = session
    return client


class CodebaseMocks:
    def __init__(self):
        self.load_application_fn = Mock()
        self.get_aws_session_or_abort_fn = Mock()
        self.input_fn = Mock(return_value="yes")
        self.echo_fn = Mock()
        self.confirm_fn = Mock()

    def params(self):
        return {
            "load_application_fn": self.load_application_fn,
            "get_aws_session_or_abort_fn": self.get_aws_session_or_abort_fn,
            "input_fn": self.input_fn,
            "echo_fn": self.echo_fn,
            "confirm_fn": self.confirm_fn,
        }


@pytest.mark.focus
def test_codebase_build_does_not_trigger_build_without_an_application():
    mocks = CodebaseMocks()
    mocks.load_application_fn.side_effect = ApplicationNotFoundError()
    codebase = Codebase(**mocks.params())

    with pytest.raises(click.Abort) as exc:
        codebase.build("not-an-application", "application", "ab1c23d")
        mocks.echo_fn.assert_has_calls(
            [
                call(
                    """The account "foo" does not contain the application "not-an-application"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
                    fg="red",
                ),
            ]
        )

@pytest.mark.focus
@patch("subprocess.run")
def test_codebase_build_does_not_trigger_without_a_valid_commit_hash(mock_subprocess_run):
    mocks = CodebaseMocks()
    codebase = Codebase(**mocks.params())

    with pytest.raises(SystemExit) as exc:
        mock_subprocess_run.return_value = MagicMock(
            stderr="The commit hash 'nonexistent-commit-hash' either does not exist or you need to run `git fetch`.",
            returncode=1,
        )

        codebase.build("test-application", "application", "nonexistent-commit-hash")
        mocks.echo_fn.assert_has_calls(
            [
                call(
                    """The commit hash "nonexistent-commit-hash" either does not exist or you need to run `git fetch`.""",
                    fg="red",
                ),
            ]
        )

@pytest.mark.focus
@patch("subprocess.run")
def test_codebase_build_does_not_trigger_build_without_confirmation(
    mock_subprocess_run
):
    mocks = CodebaseMocks()
    mocks.confirm_fn.return_value = False
    codebase = Codebase(**mocks.params())
    
    mock_subprocess_run.return_value.stderr = ""

    codebase.build("test-application", "application", "ab1c234")
    
    mocks.echo_fn.assert_has_calls(
                [
                    call(
                        """Your build was not triggered.""",
                    ),
                ]
            )
    
@pytest.mark.focus
def test_codebase_deploy_successfully_triggers_a_pipeline_based_deploy():
    mocks = CodebaseMocks()
    mocks.confirm_fn.return_value = True
    mock_application = Application(name="test-application")
    mock_application.environments = {"development": Environment(name="development", account_id="1234", sessions={"111111111111": mocks.get_aws_session_or_abort_fn})}
    mocks.load_application_fn.return_value = mock_application

    client = mock_aws_client(mocks.get_aws_session_or_abort_fn)

    client.get_parameter.return_value = {
        "Parameter": {"Value": json.dumps({"name": "application"})},
    }
    client.start_build.return_value = {
        "build": {
            "arn": "arn:aws:codebuild:eu-west-2:111111111111:build/build-project:build-id",
        },
    }

    codebase = Codebase(**mocks.params())
    codebase.deploy("test-application", "development", "application", "ab1c23d")

    client.start_build.assert_called_with(
        projectName="pipeline-test-application-application-BuildProject",
        artifactsOverride={"type": "NO_ARTIFACTS"},
        sourceTypeOverride="NO_SOURCE",
        environmentVariablesOverride=[
            {"name": "COPILOT_ENVIRONMENT", "value": "development"},
            {"name": "IMAGE_TAG", "value": "commit-ab1c23d"},
        ],
    )

    mocks.confirm_fn.assert_has_calls(
        [
        call(
            'You are about to deploy "test-application" for "application" with commit '
            '"ab1c23d" to the "development" environment. Do you want to continue?'
        ),
        ]
    )

    mocks.echo_fn.assert_has_calls(
       [
        call(
        "Your deployment has been triggered. Check your build progress in the AWS Console: "
        "https://eu-west-2.console.aws.amazon.com/codesuite/codebuild/111111111111/projects/build"
        "-project/build/build-project%3Abuild-id"
        )
       ] 
    ) 
    