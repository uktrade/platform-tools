import json
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

import boto3
import click
import pytest

from dbt_platform_helper.domain.codebase import Codebase
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import ApplicationNotFoundError
from dbt_platform_helper.utils.application import Environment

real_ecr_client = boto3.client("ecr")
real_ssm_client = boto3.client("ssm")


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
        self.confirm_fn = Mock(return_value=True)

    def params(self):
        return {
            "load_application_fn": self.load_application_fn,
            "get_aws_session_or_abort_fn": self.get_aws_session_or_abort_fn,
            "input_fn": self.input_fn,
            "echo_fn": self.echo_fn,
            "confirm_fn": self.confirm_fn,
        }


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


@patch("subprocess.run")
def test_codebase_build_does_not_trigger_build_without_confirmation(mock_subprocess_run):
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


def test_codebase_deploy_successfully_triggers_a_pipeline_based_deploy():
    mocks = CodebaseMocks()
    mocks.confirm_fn.return_value = True
    mock_application = Application(name="test-application")
    mock_application.environments = {
        "development": Environment(
            name="development",
            account_id="1234",
            sessions={"111111111111": mocks.get_aws_session_or_abort_fn},
        )
    }
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


def test_codebase_deploy_aborts_with_a_nonexistent_image_repository():
    mocks = CodebaseMocks()

    client = mock_aws_client(mocks.get_aws_session_or_abort_fn)

    client.get_parameter.return_value = {
        "Parameter": {"Value": json.dumps({"name": "application"})},
    }
    client.exceptions.ImageNotFoundException = real_ecr_client.exceptions.ImageNotFoundException
    client.exceptions.RepositoryNotFoundException = (
        real_ecr_client.exceptions.RepositoryNotFoundException
    )
    client.describe_images.side_effect = real_ecr_client.exceptions.RepositoryNotFoundException(
        {}, ""
    )

    with pytest.raises(click.Abort) as exc:
        codebase = Codebase(**mocks.params())
        codebase.deploy("test-application", "development", "application", "nonexistent-commit-hash")

        mocks.echo_fn.assert_has_calls(
            [call('The ECR Repository for codebase "application" does not exist.')]
        )


def test_codebase_deploy_aborts_with_a_nonexistent_image_tag():
    mocks = CodebaseMocks()

    client = mock_aws_client(mocks.get_aws_session_or_abort_fn)

    client.get_parameter.return_value = {
        "Parameter": {"Value": json.dumps({"name": "application"})},
    }
    client.exceptions.ImageNotFoundException = real_ecr_client.exceptions.ImageNotFoundException
    client.exceptions.RepositoryNotFoundException = (
        real_ecr_client.exceptions.RepositoryNotFoundException
    )

    client.describe_images.side_effect = real_ecr_client.exceptions.ImageNotFoundException({}, "")

    with pytest.raises(click.Abort) as exc:
        codebase = Codebase(**mocks.params())
        codebase.deploy("test-application", "development", "application", "nonexistent-commit-hash")

        mocks.echo_fn.assert_has_calls(
            [
                call(
                    f'The commit hash "nonexistent-commit-hash" has not been built into an image, try the `platform-helper codebase build` command first.'
                )
            ]
        )


@patch("subprocess.run")
def test_codebase_deploy_does_not_trigger_build_without_confirmation(mock_subprocess_run):
    mocks = CodebaseMocks()
    mock_subprocess_run.return_value.stderr = ""
    mocks.confirm_fn.return_value = False
    client = mock_aws_client(mocks.get_aws_session_or_abort_fn)

    client.get_parameter.return_value = {
        "Parameter": {"Value": json.dumps({"name": "application"})},
    }
    client.exceptions.ImageNotFoundException = real_ecr_client.exceptions.ImageNotFoundException
    client.exceptions.RepositoryNotFoundException = (
        real_ecr_client.exceptions.RepositoryNotFoundException
    )
    client.exceptions.ParameterNotFound = real_ssm_client.exceptions.ParameterNotFound
    client.start_build.return_value = {
        "build": {
            "arn": "arn:aws:codebuild:eu-west-2:111111111111:build/build-project:build-id",
        },
    }

    codebase = Codebase(**mocks.params())
    codebase.deploy("test-application", "development", "application", "ab1c23d")

    mocks.confirm_fn.assert_has_calls(
        [
            call(
                'You are about to deploy "test-application" for "application" with commit '
                '"ab1c23d" to the "development" environment. Do you want to continue?'
            ),
        ]
    )

    mocks.echo_fn.assert_has_calls([call("Your deployment was not triggered.")])


def test_codebase_deploy_does_not_trigger_build_without_an_application():
    mocks = CodebaseMocks()
    mocks.load_application_fn.side_effect = ApplicationNotFoundError()
    codebase = Codebase(**mocks.params())

    with pytest.raises(click.Abort) as exc:
        codebase.deploy("not-an-application", "dev", "application", "ab1c23d")
        mocks.echo_fn.assert_has_calls(
            [
                call(
                    """The account "foo" does not contain the application "not-an-application"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
                    fg="red",
                ),
            ]
        )


def test_codebase_deploy_does_not_trigger_build_with_missing_environment():
    mocks = CodebaseMocks()
    mock_application = Application(name="test-application")
    mock_application.environments = {}
    mocks.load_application_fn.return_value = mock_application
    codebase = Codebase(**mocks.params())

    with pytest.raises(click.Abort) as exc:
        codebase.deploy("test-application", "not-an-environment", "application", "ab1c23d")
        mocks.echo_fn.assert_has_calls(
            [
                call(
                    """The environment "not-an-environment" either does not exist or has not been deployed.""",
                    fg="red",
                ),
            ]
        )


def test_codebase_list_does_not_trigger_build_without_an_application():
    mocks = CodebaseMocks()
    mocks.load_application_fn.side_effect = ApplicationNotFoundError()
    codebase = Codebase(**mocks.params())

    with pytest.raises(click.Abort) as exc:
        codebase.list("not-an-application", True)
        mocks.echo_fn.assert_has_calls(
            [
                call(
                    """The account "foo" does not contain the application "not-an-application"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
                    fg="red",
                ),
            ]
        )


def test_lists_codebases_with_multiple_pages_of_images():
    mocks = CodebaseMocks()
    codebase = Codebase(**mocks.params())
    client = mock_aws_client(mocks.get_aws_session_or_abort_fn)
    client.get_parameters_by_path.return_value = {
        "Parameters": [
            {"Value": json.dumps({"name": "application", "repository": "uktrade/example"})}
        ],
    }

    client.get_paginator.return_value.paginate.return_value = [
        {
            "imageDetails": [
                {
                    "imageTags": ["latest", "tag-latest", "tag-1.0", "commit-10"],
                    "imagePushedAt": datetime(2023, 11, 10, 00, 00, 00),
                },
                {
                    "imageTags": ["branch-main", "commit-9"],
                    "imagePushedAt": datetime(2023, 11, 9, 00, 00, 00),
                },
            ]
        },
        {
            "imageDetails": [
                {
                    "imageTags": ["commit-8"],
                    "imagePushedAt": datetime(2023, 11, 8, 00, 00, 00),
                },
                {
                    "imageTags": ["commit-7"],
                    "imagePushedAt": datetime(2023, 11, 7, 00, 00, 00),
                },
            ]
        },
    ]
    codebase.list("test-application", True)

    mocks.echo_fn.assert_has_calls(
        [
            call("- application (https://github.com/uktrade/example)"),
            call(
                "  - https://github.com/uktrade/example/commit/10 - published: 2023-11-10 00:00:00"
            ),
            call(
                "  - https://github.com/uktrade/example/commit/9 - published: 2023-11-09 00:00:00"
            ),
            call(
                "  - https://github.com/uktrade/example/commit/8 - published: 2023-11-08 00:00:00"
            ),
            call(
                "  - https://github.com/uktrade/example/commit/7 - published: 2023-11-07 00:00:00"
            ),
            call(""),
        ]
    )


def test_lists_codebases_with_disordered_images_in_chronological_order():
    mocks = CodebaseMocks()
    codebase = Codebase(**mocks.params())
    client = mock_aws_client(mocks.get_aws_session_or_abort_fn)
    client.get_parameters_by_path.return_value = {
        "Parameters": [
            {"Value": json.dumps({"name": "application", "repository": "uktrade/example"})}
        ],
    }
    client.get_paginator.return_value.paginate.return_value = [
        {
            "imageDetails": [
                {
                    "imageTags": ["latest", "tag-latest", "tag-1.0", "commit-4"],
                    "imagePushedAt": datetime(2023, 11, 4, 00, 00, 00),
                },
                {
                    "imageTags": ["branch-main", "commit-2"],
                    "imagePushedAt": datetime(2023, 11, 2, 00, 00, 00),
                },
            ]
        },
        {
            "imageDetails": [
                {
                    "imageTags": ["commit-1"],
                    "imagePushedAt": datetime(2023, 11, 1, 00, 00, 00),
                },
                {
                    "imageTags": ["commit-3"],
                    "imagePushedAt": datetime(2023, 11, 3, 00, 00, 00),
                },
            ]
        },
    ]
    codebase.list("test-application", True)

    mocks.echo_fn.assert_has_calls(
        [
            call("The following codebases are available:"),
            call("- application (https://github.com/uktrade/example)"),
            call(
                "  - https://github.com/uktrade/example/commit/4 - published: 2023-11-04 00:00:00"
            ),
            call(
                "  - https://github.com/uktrade/example/commit/3 - published: 2023-11-03 00:00:00"
            ),
            call(
                "  - https://github.com/uktrade/example/commit/2 - published: 2023-11-02 00:00:00"
            ),
            call(
                "  - https://github.com/uktrade/example/commit/1 - published: 2023-11-01 00:00:00"
            ),
        ]
    )


def test_lists_codebases_with_images_successfully():
    mocks = CodebaseMocks()
    codebase = Codebase(**mocks.params())
    client = mock_aws_client(mocks.get_aws_session_or_abort_fn)
    client.get_parameters_by_path.return_value = {
        "Parameters": [
            {"Value": json.dumps({"name": "application", "repository": "uktrade/example"})}
        ],
    }
    client.get_paginator.return_value.paginate.return_value = [
        {
            "imageDetails": [
                {
                    "imageTags": ["latest", "tag-latest", "tag-1.0", "commit-ee4a82c"],
                    "imagePushedAt": datetime(2023, 11, 8, 17, 55, 35),
                },
                {
                    "imageTags": ["branch-main", "commit-d269d51"],
                    "imagePushedAt": datetime(2023, 11, 8, 17, 20, 34),
                },
                {
                    "imageTags": ["cache"],
                    "imagePushedAt": datetime(2023, 11, 8, 10, 31, 8),
                },
                {
                    "imageTags": ["commit-57c0a08"],
                    "imagePushedAt": datetime(2023, 11, 1, 17, 37, 2),
                },
            ]
        }
    ]

    codebase.list("test-application", True)

    mocks.echo_fn.assert_has_calls(
        [
            call("The following codebases are available:"),
            call("- application (https://github.com/uktrade/example)"),
            call(
                "  - https://github.com/uktrade/example/commit/ee4a82c - published: 2023-11-08 17:55:35"
            ),
            call(
                "  - https://github.com/uktrade/example/commit/d269d51 - published: 2023-11-08 17:20:34"
            ),
            call(
                "  - https://github.com/uktrade/example/commit/57c0a08 - published: 2023-11-01 17:37:02"
            ),
            call(""),
        ]
    )
