import filecmp
import json
import os
import stat
import subprocess
from datetime import datetime
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
from dbt_platform_helper.domain.codebase import Codebase
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
        # Arrange
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
        mock_codebase_object_instance.build.assert_called_once_with("not-an-application", "application", "ab1c23d")
        assert result.exit_code == 1

    @patch("dbt_platform_helper.commands.codebase.Codebase")
    def test_codebase_build_aborts_with_a_nonexistent_commit_hash(
        self, mock_codebase_object
    ):
        # Arrange
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

        mock_codebase_object_instance.build.assert_called_once_with("test-application", "application", "nonexistent-commit-hash")
        assert result.exit_code == 1


class TestCodebaseDeploy:
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    def test_codebase_deploy_successfully_triggers_a_pipeline_based_deploy(
        self, get_aws_session_or_abort
    ):
        from dbt_platform_helper.commands.codebase import deploy

        client = mock_aws_client(get_aws_session_or_abort)

        client.get_parameter.return_value = {
            "Parameter": {"Value": json.dumps({"name": "application"})},
        }
        client.start_build.return_value = {
            "build": {
                "arn": "arn:aws:codebuild:eu-west-2:111111111111:build/build-project:build-id",
            },
        }

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

        client.start_build.assert_called_with(
            projectName="pipeline-test-application-application-BuildProject",
            artifactsOverride={"type": "NO_ARTIFACTS"},
            sourceTypeOverride="NO_SOURCE",
            environmentVariablesOverride=[
                {"name": "COPILOT_ENVIRONMENT", "value": "development"},
                {"name": "IMAGE_TAG", "value": "commit-ab1c23d"},
            ],
        )

        assert (
            'You are about to deploy "test-application" for "application" with commit '
            '"ab1c23d" to the "development" environment. Do you want to continue?' in result.output
        )
        assert (
            "Your deployment has been triggered. Check your build progress in the AWS Console: "
            "https://eu-west-2.console.aws.amazon.com/codesuite/codebuild/111111111111/projects/build"
            "-project/build/build-project%3Abuild-id" in result.output
        )

    @patch("subprocess.run")
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    def test_codebase_deploy_aborts_with_a_nonexistent_image_repository(
        self, get_aws_session_or_abort, mock_subprocess_run
    ):
        from dbt_platform_helper.commands.codebase import deploy

        client = mock_aws_client(get_aws_session_or_abort)

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

        assert 'The ECR Repository for codebase "application" does not exist.' in result.output

    @patch("subprocess.run")
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    def test_codebase_deploy_aborts_with_a_nonexistent_image_tag(
        self, get_aws_session_or_abort, mock_subprocess_run
    ):
        from dbt_platform_helper.commands.codebase import deploy

        client = mock_aws_client(get_aws_session_or_abort)

        client.get_parameter.return_value = {
            "Parameter": {"Value": json.dumps({"name": "application"})},
        }
        client.exceptions.ImageNotFoundException = real_ecr_client.exceptions.ImageNotFoundException
        client.exceptions.RepositoryNotFoundException = (
            real_ecr_client.exceptions.RepositoryNotFoundException
        )
        client.describe_images.side_effect = real_ecr_client.exceptions.ImageNotFoundException(
            {}, ""
        )

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

        assert (
            'The commit hash "nonexistent-commit-hash" has not been built into an image, try the '
            "`platform-helper codebase build` command first." in result.output
        )

    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    def test_codebase_deploy_does_not_trigger_build_without_confirmation(
        self, get_aws_session_or_abort
    ):
        from dbt_platform_helper.commands.codebase import deploy

        client = mock_aws_client(get_aws_session_or_abort)
        client.get_parameter.return_value = {
            "Parameter": {"Value": json.dumps({"name": "application"})},
        }
        client.exceptions.ImageNotFoundException = real_ecr_client.exceptions.ImageNotFoundException
        client.exceptions.RepositoryNotFoundException = (
            real_ecr_client.exceptions.RepositoryNotFoundException
        )
        client.exceptions.ParameterNotFound = real_ssm_client.exceptions.ParameterNotFound

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
            input="n\n",
        )

        assert (
            'You are about to deploy "test-application" for "application" with commit '
            '"ab1c23d" to the "development" environment. Do you want to continue?' in result.output
        )
        assert """Your deployment was not triggered.""" in result.output

    @patch(
        "dbt_platform_helper.commands.codebase.load_application",
        side_effect=ApplicationNotFoundError,
    )
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    def test_codebase_deploy_does_not_trigger_build_without_an_application(
        self, get_aws_session_or_abort, aws_credentials
    ):
        from dbt_platform_helper.commands.codebase import deploy

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

        assert (
            """The account "foo" does not contain the application "not-an-application"; ensure you have set the environment variable "AWS_PROFILE" correctly."""
            in result.output
        )

    @patch("dbt_platform_helper.utils.application.get_aws_session_or_abort", return_value=boto3)
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    def test_codebase_deploy_does_not_trigger_build_with_missing_environment(
        self, get_aws_session_or_abort, aws_credentials, mock_application
    ):
        from dbt_platform_helper.commands.codebase import deploy

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

        assert (
            'The environment "not-an-environment" either does not exist or has not been deployed.'
            in result.output
        )


class TestCodebaseList:
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    def test_lists_codebases_successfully(self, get_aws_session_or_abort):
        client = mock_aws_client(get_aws_session_or_abort)
        client.get_parameters_by_path.return_value = {
            "Parameters": [
                {"Value": json.dumps({"name": "application", "repository": "uktrade/example"})}
            ],
        }
        from dbt_platform_helper.commands.codebase import list

        result = CliRunner().invoke(list, ["--app", "test-application"])

        assert "The following codebases are available:" in result.output
        assert "- application (https://github.com/uktrade/example)" in result.output

    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    def test_lists_codebases_with_images_successfully(self, get_aws_session_or_abort):
        client = mock_aws_client(get_aws_session_or_abort)
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
        from dbt_platform_helper.commands.codebase import list

        result = CliRunner().invoke(list, ["--app", "test-application", "--with-images"])

        assert "The following codebases are available:" in result.output
        assert "- application (https://github.com/uktrade/example)" in result.output
        assert (
            "- https://github.com/uktrade/example/commit/ee4a82c - published: 2023-11-08 17:55:35"
            in result.output
        )
        assert (
            "- https://github.com/uktrade/example/commit/d269d51 - published: 2023-11-08 17:20:34"
            in result.output
        )
        assert (
            "- https://github.com/uktrade/example/commit/57c0a08 - published: 2023-11-01 17:37:02"
            in result.output
        )

    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    def test_lists_codebases_with_multiple_pages_of_images(self, get_aws_session_or_abort):
        client = mock_aws_client(get_aws_session_or_abort)
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
        from dbt_platform_helper.commands.codebase import list

        result = CliRunner().invoke(list, ["--app", "test-application", "--with-images"])
        assert (
            "- https://github.com/uktrade/example/commit/10 - published: 2023-11-10 00:00:00"
            in result.output
        )
        assert (
            "- https://github.com/uktrade/example/commit/9 - published: 2023-11-09 00:00:00"
            in result.output
        )
        assert (
            "- https://github.com/uktrade/example/commit/8 - published: 2023-11-08 00:00:00"
            in result.output
        )
        assert (
            "- https://github.com/uktrade/example/commit/7 - published: 2023-11-07 00:00:00"
            in result.output
        )

    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    def test_lists_codebases_with_disordered_images_in_chronological_order(
        self, get_aws_session_or_abort
    ):
        client = mock_aws_client(get_aws_session_or_abort)
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
        from dbt_platform_helper.commands.codebase import list

        result = CliRunner().invoke(list, ["--app", "test-application", "--with-images"])

        assert (
            result.output.index("commit/4")
            < result.output.index("commit/3")
            < result.output.index("commit/2")
            < result.output.index("commit/1")
        )

    @patch(
        "dbt_platform_helper.commands.codebase.load_application",
        side_effect=ApplicationNotFoundError,
    )
    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    def test_aborts_when_application_does_not_exist(self, mock_aws_session, load_application):
        from dbt_platform_helper.commands.codebase import list

        os.environ["AWS_PROFILE"] = "foo"
        result = CliRunner().invoke(list, ["--app", "not-an-application"])

        assert (
            """The account "foo" does not contain the application "not-an-application"; ensure you have set the environment variable "AWS_PROFILE" correctly."""
            in result.output
        )

    @patch("dbt_platform_helper.commands.codebase.get_aws_session_or_abort")
    def test_aborts_when_application_has_no_codebases(self, get_aws_session_or_abort):
        from dbt_platform_helper.commands.codebase import list

        client = mock_aws_client(get_aws_session_or_abort)

        client.get_parameters_by_path.return_value = {"Parameters": []}

        result = CliRunner().invoke(list, ["--app", "test-application"])

        assert 'No codebases found for application "test-application"' in result.output


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
