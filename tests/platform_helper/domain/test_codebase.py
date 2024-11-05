from unittest import mock
from unittest.mock import MagicMock, Mock, call, patch

import click
import pytest

from dbt_platform_helper.domain.codebase import Codebase
from dbt_platform_helper.utils.application import ApplicationNotFoundError


class CodebaseMocks:
    def __init__(self):
        self.load_application_fn = Mock()
        self.get_aws_session_or_abort_fn = Mock()
        self.input_fn = Mock(return_value="yes")
        self.echo_fn = Mock()

    def params(self):
        return {
            "load_application_fn": self.load_application_fn,
            "get_aws_session_or_abort_fn": self.get_aws_session_or_abort_fn,
            "input_fn": self.input_fn,
            "echo_fn": self.echo_fn,
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
@patch("click.confirm")
@patch("subprocess.run")
def test_codebase_build_does_not_trigger_build_without_confirmation(
    mock_subprocess_run, mock_click_confirm
):
    mocks = CodebaseMocks()
    codebase = Codebase(**mocks.params())
    
    mock_subprocess_run.return_value.stderr = ""
    mock_click_confirm.return_value = False

    codebase.build("test-application", "application", "ab1c234")
    
    mocks.echo_fn.assert_has_calls(
                [
                    call(
                        """Your build was not triggered.""",
                    ),
                ]
            )