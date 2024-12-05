import filecmp
import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import PropertyMock
from unittest.mock import call
from unittest.mock import patch

import boto3
import pytest
import requests

from dbt_platform_helper.domain.codebase import ApplicationDeploymentNotTriggered
from dbt_platform_helper.domain.codebase import ApplicationEnvironmentNotFoundError
from dbt_platform_helper.domain.codebase import Codebase
from dbt_platform_helper.domain.codebase import NotInCodeBaseRepositoryError
from dbt_platform_helper.legacy_exceptions import CopilotCodebaseNotFoundError
from dbt_platform_helper.legacy_exceptions import ImageNotFoundError
from dbt_platform_helper.utils.application import ApplicationNotFoundError
from dbt_platform_helper.utils.application import Environment
from dbt_platform_helper.utils.git import CommitNotFoundError
from tests.platform_helper.conftest import EXPECTED_FILES_DIR

ecr_exceptions = boto3.client("ecr").exceptions
ssm_exceptions = boto3.client("ssm").exceptions


def mock_aws_client(get_aws_session_or_abort):
    session = MagicMock(name="session-mock")
    client = MagicMock(name="client-mock")
    session.client.return_value = client
    get_aws_session_or_abort.return_value = session
    return client


class CodebaseMocks:
    def __init__(self, **kwargs):
        self.load_application = kwargs.get("load_application", Mock())
        self.get_aws_session_or_abort = kwargs.get("get_aws_session_or_abort", Mock())
        self.input = kwargs.get("input", Mock(return_value="yes"))
        self.echo = kwargs.get("echo", Mock())
        self.confirm = kwargs.get("confirm", Mock(return_value=True))
        self.check_codebase_exists = kwargs.get(
            "check_codebase_exists",
            Mock(
                return_value="""
                                             {
                                                "name": "test-app", 
                                                "repository": "uktrade/test-app",
                                                "services": "1234"
                                             }
                                        """
            ),
        )
        self.check_image_exists = kwargs.get("check_image_exists", Mock(return_value=""))
        self.run_subprocess = kwargs.get("run_subprocess", Mock())
        self.check_if_commit_exists = kwargs.get("check_if_commit_exists", Mock())

    def params(self):
        return {
            "load_application": self.load_application,
            "get_aws_session_or_abort": self.get_aws_session_or_abort,
            "check_codebase_exists": self.check_codebase_exists,
            "check_image_exists": self.check_image_exists,
            "input": self.input,
            "echo": self.echo,
            "confirm": self.confirm,
            "run_subprocess": self.run_subprocess,
            "check_if_commit_exists": self.check_if_commit_exists,
        }


@patch("requests.get")
def test_codebase_prepare_generates_the_expected_files(mocked_requests_get, tmp_path):
    mocks = CodebaseMocks()
    codebase = Codebase(**mocks.params())
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

    mocks.run_subprocess.return_value.stdout = "git@github.com:uktrade/test-app.git"

    codebase.prepare()

    expected_files_dir = Path(EXPECTED_FILES_DIR) / ".copilot"
    copilot_dir = Path.cwd() / ".copilot"

    compare_directories = filecmp.dircmp(str(expected_files_dir), str(copilot_dir))

    mocks.echo.assert_has_calls(
        [
            call(
                "File .copilot/image_build_run.sh created",
            ),
            call(
                "File .copilot/config.yml created",
            ),
            call(
                "File phases/build.sh created",
            ),
            call(
                "File phases/install.sh created",
            ),
            call(
                "File phases/post_build.sh created",
            ),
            call(
                "File phases/pre_build.sh created",
            ),
        ]
    )

    assert is_same_files(compare_directories) is True


def test_codebase_prepare_does_not_generate_files_in_a_repo_with_a_copilot_directory(tmp_path):
    mocks = CodebaseMocks()
    mocks.load_application.side_effect = SystemExit(1)
    codebase = Codebase(**mocks.params())
    os.chdir(tmp_path)
    Path(tmp_path / "copilot").mkdir()

    mocks.run_subprocess.return_value.stdout = mock_run_suprocess_fixture()

    with pytest.raises(NotInCodeBaseRepositoryError):
        codebase.prepare()


def test_codebase_build_does_not_trigger_build_without_an_application():
    mocks = CodebaseMocks()
    mocks.load_application.side_effect = ApplicationNotFoundError("not-an-application")
    codebase = Codebase(**mocks.params())

    with pytest.raises(ApplicationNotFoundError):
        codebase.build("not-an-application", "application", "ab1c23d")
        mocks.echo.assert_has_calls(
            [
                call(
                    """The account "foo" does not contain the application "not-an-application"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
                    fg="red",
                ),
            ]
        )


def test_codebase_build_commit_not_found():
    mocks = CodebaseMocks(check_if_commit_exists=Mock(side_effect=CommitNotFoundError()))

    codebase = Codebase(**mocks.params())

    with pytest.raises(CommitNotFoundError):
        codebase.build("not-an-application", "application", "ab1c23d")


def test_codebase_prepare_raises_not_in_codebase_exception(tmp_path):
    mocks = CodebaseMocks()
    mocks.load_application.side_effect = SystemExit(1)

    mocks.run_subprocess.return_value = mock_run_suprocess_fixture()
    codebase = Codebase(**mocks.params())
    os.chdir(tmp_path)
    Path(tmp_path / "copilot").mkdir()

    with pytest.raises(NotInCodeBaseRepositoryError):
        codebase.prepare()


def test_codebase_prepare_generates_an_executable_image_build_run_file(tmp_path):
    mocks = CodebaseMocks()
    codebase = Codebase(**mocks.params())
    os.chdir(tmp_path)
    mocks.run_subprocess.return_value.stdout = "demodjango"

    codebase.prepare()

    image_build_run_path = Path(".copilot/image_build_run.sh")
    assert image_build_run_path.exists()
    assert image_build_run_path.is_file()
    assert os.access(image_build_run_path, os.X_OK)


def test_codebase_build_does_not_trigger_deployment_without_confirmation():
    mocks = CodebaseMocks(confirm=Mock(return_value=False))

    client = mock_aws_client(mocks.get_aws_session_or_abort)
    client.get_parameter.return_value = {
        "Parameter": {"Value": json.dumps({"name": "application"})},
    }

    with pytest.raises(ApplicationDeploymentNotTriggered) as exc:
        codebase = Codebase(**mocks.params())
        codebase.build("test-application", "application", "ab1c234")


def test_codebase_deploy_successfully_triggers_a_pipeline_based_deploy(mock_application):
    mocks = CodebaseMocks()
    mocks.confirm.return_value = True
    mock_application.environments = {
        "development": Environment(
            name="development",
            account_id="1234",
            sessions={"111111111111": mocks.get_aws_session_or_abort},
        )
    }
    mocks.load_application.return_value = mock_application

    client = mock_aws_client(mocks.get_aws_session_or_abort)

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

    mocks.confirm.assert_has_calls(
        [
            call(
                'You are about to deploy "test-application" for "application" with commit '
                '"ab1c23d" to the "development" environment. Do you want to continue?'
            ),
        ]
    )

    mocks.echo.assert_has_calls(
        [
            call(
                "Your deployment has been triggered. Check your build progress in the AWS Console: "
                "https://eu-west-2.console.aws.amazon.com/codesuite/codebuild/111111111111/projects/build"
                "-project/build/build-project%3Abuild-id"
            )
        ]
    )


def test_codebase_deploy_exception_with_a_nonexistent_codebase():
    mocks = CodebaseMocks(
        check_codebase_exists=Mock(side_effect=CopilotCodebaseNotFoundError("application"))
    )

    client = mock_aws_client(mocks.get_aws_session_or_abort)

    client.get_parameter.return_value = {
        "Parameter": {"Value": json.dumps({"name": "application"})},
    }

    with pytest.raises(CopilotCodebaseNotFoundError):
        codebase = Codebase(**mocks.params())
        codebase.deploy("test-application", "development", "application", "nonexistent-commit-hash")


def test_check_codebase_exists_returns_error_when_no_json():
    mocks = CodebaseMocks(
        check_codebase_exists=Mock(side_effect=CopilotCodebaseNotFoundError("application"))
    )

    client = mock_aws_client(mocks.get_aws_session_or_abort)

    client.get_parameter.return_value = {
        "Parameter": {"Value": json.dumps({"name": "application"})},
    }

    with pytest.raises(CopilotCodebaseNotFoundError):
        codebase = Codebase(**mocks.params())
        codebase.deploy("test-application", "development", "application", "nonexistent-commit-hash")


def test_codebase_deploy_aborts_with_a_nonexistent_image_repository():
    mocks = CodebaseMocks(
        check_image_exists=Mock(side_effect=ImageNotFoundError("nonexistent-commit-hash"))
    )

    client = mock_aws_client(mocks.get_aws_session_or_abort)

    client.get_parameter.return_value = {
        "Parameter": {"Value": json.dumps({"name": "application"})},
    }
    client.describe_images.side_effect = ecr_exceptions.RepositoryNotFoundException({}, "")

    with pytest.raises(ImageNotFoundError):
        codebase = Codebase(**mocks.params())
        codebase.deploy("test-application", "development", "application", "nonexistent-commit-hash")


def test_codebase_deploy_aborts_with_a_nonexistent_image_tag():
    mocks = CodebaseMocks(
        check_image_exists=Mock(side_effect=ImageNotFoundError("nonexistent-commit-hash"))
    )

    client = mock_aws_client(mocks.get_aws_session_or_abort)

    client.get_parameter.return_value = {
        "Parameter": {"Value": json.dumps({"name": "application"})},
    }
    client.describe_images.side_effect = ecr_exceptions.ImageNotFoundException({}, "")

    with pytest.raises(ImageNotFoundError):
        codebase = Codebase(**mocks.params())
        codebase.deploy("test-application", "development", "application", "nonexistent-commit-hash")


def test_codebase_deploy_does_not_trigger_build_without_confirmation():
    mocks = CodebaseMocks()
    mocks.run_subprocess.return_value.stderr = ""
    mocks.confirm.return_value = False
    client = mock_aws_client(mocks.get_aws_session_or_abort)

    client.get_parameter.return_value = {
        "Parameter": {"Value": json.dumps({"name": "application"})},
    }
    client.exceptions.ParameterNotFound = ssm_exceptions.ParameterNotFound
    client.start_build.return_value = {
        "build": {
            "arn": "arn:aws:codebuild:eu-west-2:111111111111:build/build-project:build-id",
        },
    }

    with pytest.raises(ApplicationDeploymentNotTriggered) as exc:
        codebase = Codebase(**mocks.params())
        codebase.deploy("test-application", "development", "application", "ab1c23d")

        mocks.confirm.assert_has_calls(
            [
                call(
                    'You are about to deploy "test-application" for "application" with commit '
                    '"ab1c23d" to the "development" environment. Do you want to continue?'
                ),
            ]
        )

        mocks.echo.assert_has_calls([call("Your deployment was not triggered.")])


def test_codebase_deploy_does_not_trigger_build_without_an_application():
    mocks = CodebaseMocks()
    mocks.load_application.side_effect = ApplicationNotFoundError("not-an-application")
    codebase = Codebase(**mocks.params())

    with pytest.raises(ApplicationNotFoundError) as exc:
        codebase.deploy("not-an-application", "dev", "application", "ab1c23d")


def test_codebase_deploy_does_not_trigger_build_with_missing_environment(mock_application):
    mocks = CodebaseMocks()
    mock_application.environments = {}
    mocks.load_application.return_value = mock_application
    codebase = Codebase(**mocks.params())

    with pytest.raises(ApplicationEnvironmentNotFoundError) as exc:
        codebase.deploy("test-application", "not-an-environment", "application", "ab1c23d")
        mocks.echo.assert_has_calls(
            [
                call(
                    """The environment "not-an-environment" either does not exist or has not been deployed.""",
                    fg="red",
                ),
            ]
        )


def test_codebase_deploy_does_not_trigger_deployment_without_confirmation():
    mocks = CodebaseMocks(confirm=Mock(return_value=False))

    client = mock_aws_client(mocks.get_aws_session_or_abort)
    client.get_parameter.return_value = {
        "Parameter": {"Value": json.dumps({"name": "application"})},
    }

    with pytest.raises(ApplicationDeploymentNotTriggered) as exc:
        codebase = Codebase(**mocks.params())
        codebase.deploy("test-application", "development", "application", "nonexistent-commit-hash")


def test_codebase_list_does_not_trigger_build_without_an_application():
    mocks = CodebaseMocks()
    mocks.load_application.side_effect = ApplicationNotFoundError("not-an-application")
    codebase = Codebase(**mocks.params())

    with pytest.raises(ApplicationNotFoundError) as exc:
        codebase.list("not-an-application", True)


def test_codebase_list_returns_empty_when_no_codebases():
    mocks = CodebaseMocks(check_codebase_exists=Mock())

    client = mock_aws_client(mocks.get_aws_session_or_abort)

    client.get_parameter.return_value = {
        "Parameter": {"Value": json.dumps({"name": "application"})},
    }

    codebase = Codebase(**mocks.params())
    codebase.list("test-application", True)

    mocks.echo.assert_has_calls([])


def test_lists_codebases_with_multiple_pages_of_images():
    mocks = CodebaseMocks()
    codebase = Codebase(**mocks.params())
    client = mock_aws_client(mocks.get_aws_session_or_abort)
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

    mocks.echo.assert_has_calls(
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
    client = mock_aws_client(mocks.get_aws_session_or_abort)
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

    mocks.echo.assert_has_calls(
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
    client = mock_aws_client(mocks.get_aws_session_or_abort)
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

    mocks.echo.assert_has_calls(
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


def mock_run_suprocess_fixture():
    mock_stdout = MagicMock()
    mock_stdout.configure_mock(**{"stdout.decode.return_value": '{"A": 3}'})
    return mock_stdout
