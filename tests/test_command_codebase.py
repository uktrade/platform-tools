import filecmp
import os
import stat
import subprocess
from pathlib import Path
from unittest.mock import PropertyMock
from unittest.mock import patch

import requests
from click.testing import CliRunner

from dbt_copilot_helper.commands.codebase import prepare
from tests.conftest import EXPECTED_FILES_DIR


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
    Path.cwd().rename(Path.cwd().parent / "test-app")

    subprocess.run(["git", "init"])

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
    Path.cwd().rename(Path.cwd().parent / "test-app-deploy")

    subprocess.run(["git", "init"])

    result = CliRunner().invoke(prepare)

    assert (
        "You are in the deploy repository; make sure you are in the application codebase repository."
        in result.stdout
    )
    assert result.exit_code == 1


def test_codebase_prepare_generates_an_executable_image_build_run_file(tmp_path):
    os.chdir(tmp_path)
    Path.cwd().rename(Path.cwd().parent / "test-app")

    subprocess.run(["git", "init"])

    result = CliRunner().invoke(prepare)

    assert result.exit_code == 0
    assert stat.filemode(Path(".copilot/image_build_run.sh").stat().st_mode) == "-rwxr--r--"


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
