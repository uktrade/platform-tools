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
from dbt_platform_helper.domain.codebase import ApplicationEnvironmentNotFoundException
from dbt_platform_helper.domain.codebase import Codebase
from dbt_platform_helper.domain.codebase import NotInCodeBaseRepositoryException
from dbt_platform_helper.providers.aws.exceptions import ImageNotFoundException
from dbt_platform_helper.providers.aws.exceptions import RepositoryNotFoundException
from dbt_platform_helper.utils.application import ApplicationNotFoundException
from dbt_platform_helper.utils.application import Environment
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
        self.parameter_provider = kwargs.get("parameter_provider", Mock())
        self.load_application = kwargs.get("load_application", Mock())
        self.get_aws_session_or_abort = kwargs.get("get_aws_session_or_abort", Mock())
        self.io = kwargs.get("io", Mock())
        self.ecr_provider = kwargs.get("ecr_provider", Mock())
        self.get_image_build_project = kwargs.get(
            "get_image_build_project",
            Mock(return_value="test-application-application-codebase-image-build"),
        )
        self.get_manual_release_pipeline = kwargs.get(
            "get_manual_release_pipeline",
            Mock(return_value="test-application-application-manual-release"),
        )
        self.run_subprocess = kwargs.get("run_subprocess", Mock())

    def params(self):
        return {
            "parameter_provider": self.parameter_provider,
            "load_application": self.load_application,
            "get_aws_session_or_abort": self.get_aws_session_or_abort,
            "ecr_provider": self.ecr_provider,
            "get_image_build_project": self.get_image_build_project,
            "get_manual_release_pipeline": self.get_manual_release_pipeline,
            "io": self.io,
            "run_subprocess": self.run_subprocess,
        }


@patch("dbt_platform_helper.domain.codebase.requests.get")
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

    mocks.io.info.assert_has_calls(
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

    with pytest.raises(NotInCodeBaseRepositoryException):
        codebase.prepare()


@mock_aws_client
def test_codebase_build_does_not_trigger_build_without_an_application():
    mocks = CodebaseMocks()
    mocks.load_application.side_effect = ApplicationNotFoundException("not-an-application")
    codebase = Codebase(**mocks.params())

    with pytest.raises(
        ApplicationNotFoundException,
        match="""The account "foo" does not contain the application "not-an-application"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
    ):
        codebase.build("not-an-application", "application", "ab1c23d")


def test_codebase_prepare_raises_not_in_codebase_exception(tmp_path):
    mocks = CodebaseMocks()
    mocks.load_application.side_effect = SystemExit(1)

    mocks.run_subprocess.return_value = mock_run_suprocess_fixture()
    codebase = Codebase(**mocks.params())
    os.chdir(tmp_path)
    Path(tmp_path / "copilot").mkdir()

    with pytest.raises(NotInCodeBaseRepositoryException):
        codebase.prepare()


@patch(
    "requests.get",
    return_value=MagicMock(
        content=b"builders:\n  - name: paketobuildpacks/builder-jammy-full\n    versions:\n      - version: 0.3.482\n      - version: 0.3.473\n      - version: 0.3.431     \n      - version: 0.3.414 \n      - version: 0.3.397\n      - version: 0.3.339\n      - version: 0.3.338\n      - version: 0.3.317\n      - version: 0.3.294\n      - version: 0.3.288\n  - name: paketobuildpacks/builder-jammy-base\n    versions:\n      - version: 0.4.409\n      - version: 0.4.398\n      - version: 0.4.378\n      - version: 0.4.279\n      - version: 0.4.278\n      - version: 0.4.258\n      - version: 0.4.240\n      - version: 0.4.239\n  - name: paketobuildpacks/builder\n    deprecated: true\n    versions:\n      - version: 0.2.443-full\n"
    ),
)
def test_codebase_prepare_generates_an_executable_image_build_run_file(requests, tmp_path):
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
    mocks = CodebaseMocks()
    mocks.io.confirm.return_value = False

    with pytest.raises(ApplicationDeploymentNotTriggered):
        codebase = Codebase(**mocks.params())
        codebase.build("test-application", "application", "ab1c234")


@pytest.mark.parametrize(
    "commit, tag, branch, expected_ref, expected_corresponding_to",
    [
        ("abc123", None, None, "commit-abc123", ""),
        ("abc1234c190419c3755de305581c2f9e4df9ece1", None, None, "commit-abc1234", ""),
        (None, "1.2.3", None, "tag-1.2.3", "(corresponding to tag 1.2.3) "),
        (None, None, "feature_one", "branch-feature_one", "(corresponding to branch feature_one) "),
    ],
)
def test_codebase_deploy_successfully_triggers_a_pipeline_based_deploy(
    mock_application, commit, tag, branch, expected_ref, expected_corresponding_to
):
    mocks = CodebaseMocks()
    mocks.io.confirm.return_value = True
    mock_application.environments = {
        "development": Environment(
            name="development",
            account_id="1234",
            sessions={"111111111111": mocks.get_aws_session_or_abort},
        )
    }
    mocks.load_application.return_value = mock_application

    client = mock_aws_client(mocks.get_aws_session_or_abort)
    client.start_pipeline_execution.return_value = {
        "pipelineExecutionId": "0abc00a0a-1abc-1ab1-1234-1ab12a1a1abc"
    }
    image_details = [{"imageTags": ["tag-1.2.3", "branch-feature_one", "commit-abc123"]}]
    mocks.ecr_provider.get_image_details.return_value = image_details
    mocks.ecr_provider.find_commit_tag.return_value = "commit-abc123"

    codebase = Codebase(**mocks.params())
    codebase.deploy("test-application", "development", "application", commit, tag, branch)

    codebase.ecr_provider.get_image_details.assert_called_once_with(
        mock_application, "application", expected_ref
    )
    codebase.ecr_provider.find_commit_tag.assert_called_once_with(image_details, expected_ref)

    client.start_pipeline_execution.assert_called_with(
        name="test-application-application-manual-release",
        variables=[
            {"name": "ENVIRONMENT", "value": "development"},
            {"name": "IMAGE_TAG", "value": "commit-abc123"},
        ],
    )

    mocks.io.confirm.assert_has_calls(
        [
            call(
                '\nYou are about to deploy "test-application" for "application" with image reference '
                f'"commit-abc123" {expected_corresponding_to}to the "development" environment using the "test-application-application-manual-release" deployment pipeline. Do you want to continue?'
            ),
        ]
    )

    mocks.io.info.assert_has_calls(
        [
            call(
                "Your deployment has been triggered. Check your build progress in the AWS Console: "
                "https://eu-west-2.console.aws.amazon.com/codesuite/codepipeline/pipelines/test-application-application-manual-release/executions/0abc00a0a-1abc-1ab1-1234-1ab12a1a1abc"
            )
        ]
    )


@pytest.mark.parametrize(
    "tag, branch, expected_find_commit_tag_param",
    [
        ("1.2.3", None, "tag-1.2.3"),
        (None, "feature_one", "branch-feature_one"),
    ],
)
def test_codebase_deploy_calls_find_commit_tag_when_ref_is_not_commit_tag(
    tag, branch, expected_find_commit_tag_param
):
    mocks = CodebaseMocks()
    mock_image_details = MagicMock()
    mocks.ecr_provider.get_image_details.return_value = mock_image_details

    client = mock_aws_client(mocks.get_aws_session_or_abort)
    client.start_pipeline_execution.return_value = {"pipelineExecutionId": "fake-execution-id"}

    mocks.ecr_provider.find_commit_tag.return_value = "commit-abc123"
    codebase = Codebase(**mocks.params())

    # 'commit' is None as we're only interested in scenarios where 'commit' is not used
    codebase.deploy("test-application", "development", "application", None, tag, branch)

    mocks.ecr_provider.find_commit_tag.assert_called_once_with(
        mock_image_details, expected_find_commit_tag_param
    )

    client.start_pipeline_execution.assert_called_once_with(
        name="test-application-application-manual-release",
        variables=[
            {"name": "ENVIRONMENT", "value": "development"},
            {"name": "IMAGE_TAG", "value": "commit-abc123"},
        ],
    )


@pytest.mark.parametrize(
    "tag, branch",
    [
        ("non-existent-tag", None),
        (None, "nonexistent-branch"),
    ],
)
def test_codebase_deploy_propagates_repository_not_found_exception(tag, branch):
    mocks = CodebaseMocks()
    mocks.ecr_provider.get_image_details.side_effect = RepositoryNotFoundException("application")

    with pytest.raises(RepositoryNotFoundException):
        codebase = Codebase(**mocks.params())
        codebase.deploy("test-application", "development", "application", None, tag, branch)


@pytest.mark.parametrize(
    "tag, branch",
    [
        (None, None),
        ("non-existent-tag", None),
        (None, "nonexistent-branch"),
    ],
)
def test_codebase_deploy_propagates_image_not_found_exception(tag, branch):
    mocks = CodebaseMocks()
    mocks.ecr_provider.get_image_details.side_effect = ImageNotFoundException("ref")

    with pytest.raises(ImageNotFoundException):
        codebase = Codebase(**mocks.params())
        codebase.deploy("test-application", "development", "application", None, tag, branch)


@pytest.mark.parametrize(
    "commit, tag, branch, expected_corresponding_to",
    [
        ("abc123", None, None, ""),
        (None, "1.2.3", None, "(corresponding to tag 1.2.3) "),
        (None, None, "test-branch", "(corresponding to branch test-branch) "),
    ],
)
def test_codebase_deploy_does_not_trigger_pipeline_build_without_confirmation(
    commit, tag, branch, expected_corresponding_to
):
    mocks = CodebaseMocks()
    mocks.run_subprocess.return_value.stderr = ""
    mocks.io.confirm.return_value = False
    client = mock_aws_client(mocks.get_aws_session_or_abort)
    mocks.ecr_provider.find_commit_tag.return_value = "commit-ab1c23d"

    with pytest.raises(ApplicationDeploymentNotTriggered) as exc:
        codebase = Codebase(**mocks.params())
        codebase.deploy("test-application", "development", "application", commit, tag, branch)

    assert str(exc.value) == "Your deployment for application was not triggered."
    assert isinstance(exc.value, ApplicationDeploymentNotTriggered)

    mocks.io.confirm.assert_has_calls(
        [
            call(
                f'\nYou are about to deploy "test-application" for "application" with image reference "commit-ab1c23d" {expected_corresponding_to}to the "development" environment using the "test-application-application-manual-release" deployment pipeline. Do you want to continue?'
            ),
        ]
    )

    client.start_pipeline_execution.assert_not_called()


@pytest.mark.parametrize(
    "commit, tag, branch",
    [
        ("abc123", None, None),
        (None, "1.2.3", None),
        (None, None, "test-branch"),
    ],
)
def test_codebase_deploy_does_not_trigger_build_without_an_application(commit, tag, branch):
    mocks = CodebaseMocks()
    mocks.load_application.side_effect = ApplicationNotFoundException("not-an-application")
    codebase = Codebase(**mocks.params())

    with pytest.raises(ApplicationNotFoundException):
        codebase.deploy("not-an-application", "dev", "application", commit, tag, branch)


@pytest.mark.parametrize(
    "commit, tag, branch",
    [
        ("abc123", None, None),
        (None, "1.2.3", None),
        (None, None, "test-branch"),
    ],
)
def test_codebase_deploy_does_not_trigger_build_with_missing_environment(
    mock_application, commit, tag, branch
):
    mocks = CodebaseMocks()
    mock_application.environments = {}
    mocks.load_application.return_value = mock_application
    codebase = Codebase(**mocks.params())

    with pytest.raises(
        ApplicationEnvironmentNotFoundException,
        match="""The environment "not-an-environment" either does not exist or has not been deployed.""",
    ):
        codebase.deploy(
            "test-application", "not-an-environment", "application", commit, tag, branch
        )


@pytest.mark.parametrize(
    "commit, tag, branch",
    [
        ("abc123", None, None),
        (None, "1.2.3", None),
        (None, None, "test-branch"),
    ],
)
def test_codebase_deploy_does_not_trigger_deployment_without_confirmation(commit, tag, branch):
    mocks = CodebaseMocks()
    mocks.io.confirm.return_value = False

    with pytest.raises(ApplicationDeploymentNotTriggered):
        codebase = Codebase(**mocks.params())
        codebase.deploy("test-application", "development", "application", commit, tag, branch)


def test_codebase_deploy_raises_error_when_no_commit_tag_or_branch_provided():
    mocks = CodebaseMocks()
    mocks.io.abort_with_error.side_effect = SystemExit(1)
    codebase = Codebase(**mocks.params())

    with pytest.raises(SystemExit) as system_exit_info:
        codebase.deploy(
            app="test-app", env="dev", codebase="application", commit=None, tag=None, branch=None
        )

    assert system_exit_info.type == SystemExit
    assert system_exit_info.value.code == 1

    mocks.io.abort_with_error.assert_called_once_with(
        "To deploy, you must provide one of the options --commit, --tag or --branch."
    )


@pytest.mark.parametrize(
    "commit, tag, branch",
    [
        ("abc123", "1.2.3", None),
        (None, "1.2.3", "test-branch"),
        ("abc123", None, "test-branch"),
        ("abc123", "1.2.3", "test-branch"),
    ],
)
def test_codebase_deploy_raises_error_when_multiple_refs_are_provided(commit, tag, branch):
    mocks = CodebaseMocks()
    mocks.io.abort_with_error.side_effect = SystemExit(1)
    codebase = Codebase(**mocks.params())

    with pytest.raises(SystemExit) as system_exit_info:
        codebase.deploy(
            app="test-app", env="dev", codebase="application", commit=commit, tag=tag, branch=branch
        )

    assert system_exit_info.type == SystemExit
    assert system_exit_info.value.code == 1

    mocks.io.abort_with_error.assert_called_once_with(
        "You have provided more than one of the --tag, --branch and --commit options but these are mutually exclusive. Please provide only one of these options."
    )


def test_codebase_list_does_not_trigger_build_without_an_application():
    mocks = CodebaseMocks()
    mocks.load_application.side_effect = ApplicationNotFoundException("not-an-application")
    codebase = Codebase(**mocks.params())

    with pytest.raises(ApplicationNotFoundException):
        codebase.list("not-an-application", True)


def test_codebase_list_returns_empty_when_no_codebases():
    mocks = CodebaseMocks(check_codebase_exists=Mock())
    mocks.parameter_provider.get_ssm_parameters_by_path.return_value = []

    codebase = Codebase(**mocks.params())
    codebase.list("test-application", True)

    mocks.io.info.assert_has_calls([])


def test_lists_codebases_with_multiple_pages_of_images():
    mocks = CodebaseMocks()
    mocks.parameter_provider.get_ssm_parameters_by_path.return_value = [
        {"Value": json.dumps({"name": "application", "repository": "uktrade/example"})}
    ]
    codebase = Codebase(**mocks.params())
    client = mock_aws_client(mocks.get_aws_session_or_abort)

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

    mocks.io.info.assert_has_calls(
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
    mocks.parameter_provider.get_ssm_parameters_by_path.return_value = [
        {"Value": json.dumps({"name": "application", "repository": "uktrade/example"})}
    ]
    codebase = Codebase(**mocks.params())
    client = mock_aws_client(mocks.get_aws_session_or_abort)

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

    mocks.io.info.assert_has_calls(
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
    mocks.parameter_provider.get_ssm_parameters_by_path.return_value = [
        {"Value": json.dumps({"name": "application", "repository": "uktrade/example"})}
    ]
    codebase = Codebase(**mocks.params())
    client = mock_aws_client(mocks.get_aws_session_or_abort)
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

    mocks.io.info.assert_has_calls(
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
