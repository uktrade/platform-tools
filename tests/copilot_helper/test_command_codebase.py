import filecmp
import json
import os
import stat
import subprocess
from pathlib import Path
from unittest.mock import PropertyMock
from unittest.mock import patch

import boto3
import requests
from click.testing import CliRunner

from dbt_copilot_helper.commands.codebase import build
from dbt_copilot_helper.commands.codebase import prepare
from tests.copilot_helper.conftest import EXPECTED_FILES_DIR


@patch("dbt_copilot_helper.commands.codebase.requests.get")
def test_codebase_prepare_generates_the_expected_files(mocked_requests_get, tmp_path):
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

    subprocess.run(["git", "init"])
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:uktrade/test-app.git"])

    result = CliRunner().invoke(prepare)

    expected_files_dir = Path(EXPECTED_FILES_DIR) / ".copilot"
    copilot_dir = Path.cwd() / ".copilot"

    compare_directories = filecmp.dircmp(str(expected_files_dir), str(copilot_dir))

    for phase in ["build", "install", "post_build", "pre_build"]:
        assert f"phases/{phase}.sh" in result.stdout

    assert result.exit_code == 0
    assert is_same_files(compare_directories) is True


def test_codebase_prepare_does_not_generate_files_in_the_deploy_repo(tmp_path):
    os.chdir(tmp_path)

    subprocess.run(["git", "init"])
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:uktrade/test-app-deploy.git"])

    result = CliRunner().invoke(prepare)

    assert (
        "You are in the deploy repository; make sure you are in the application codebase repository."
        in result.stdout
    )
    assert result.exit_code == 1


def test_codebase_prepare_does_not_generate_files_in_a_repo_with_a_copilot_directory(tmp_path):
    os.chdir(tmp_path)
    Path(tmp_path / "copilot").mkdir()

    subprocess.run(["git", "init"])
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:uktrade/some-test-app.git"])

    result = CliRunner().invoke(prepare)

    assert (
        "You are in the deploy repository; make sure you are in the application codebase repository."
        in result.stdout
    )
    assert result.exit_code == 1


def test_codebase_prepare_generates_an_executable_image_build_run_file(tmp_path):
    os.chdir(tmp_path)

    subprocess.run(["git", "init"])
    subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:uktrade/another-test-app.git"]
    )

    result = CliRunner().invoke(prepare)

    assert result.exit_code == 0
    assert stat.filemode(Path(".copilot/image_build_run.sh").stat().st_mode) == "-rwxr--r--"


@patch("boto3.client")
@patch("click.confirm")
@patch("subprocess.run")
@patch("dbt_copilot_helper.utils.application.get_aws_session_or_abort", return_value=boto3)
def test_codebase_build(
    get_aws_session_or_abort, mock_subprocess_run, mock_click_confirm, mock_boto_client
):
    mock_subprocess_run.return_value.stderr = ""
    mock_click_confirm.return_value = "y"
    ssm_client = boto3.client("ssm")

    ssm_client.put_parameter(
        Name=f"/copilot/applications/test-application",
        Value=json.dumps(
            {
                "name": "test-application",
                "account": "111111111",
            },
        ),
        Type="String",
    )

    result = CliRunner().invoke(
        build,
        [
            "--app",
            "test-application",
            "--codebase",
            "application",
            "--commit",
            "ee4a82c",
        ],
    )

    mock_boto_client.return_value.start_build.assert_called_with(
        projectName="codebuild-test-application-application",
        artifactsOverride={"type": "NO_ARTIFACTS"},
        sourceVersion="ee4a82c",
    )

    assert (
        "Your build has been triggered and you can check your build progress in the AWS Console."
        in result.output
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
