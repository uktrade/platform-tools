from unittest.mock import Mock
from unittest.mock import patch

import pytest

import dbt_platform_helper.utils.git
from dbt_platform_helper.platform_exception import PlatformException


def test_extract_repository_name_from_ssh_clone():
    result = dbt_platform_helper.utils.git.extract_repository_name(
        "git@github.com:uktrade/platform-tools.git"
    )
    assert result == "uktrade/platform-tools"


def test_doesnt_fail_when_no_git_repo():
    result = dbt_platform_helper.utils.git.extract_repository_name(None)
    assert result == None


def test_extract_repository_name_from_https_clone():
    result = dbt_platform_helper.utils.git.extract_repository_name(
        "https://github.com/uktrade/platform-tools.git"
    )
    assert result == "uktrade/platform-tools"


@patch("subprocess.run")
def test_repository_name_fetched_from_subprocess(subprocess_run):
    mock_stdout = Mock(**{"stdout.strip.return_value": "https://github.com/testorg/testrepo.git"})
    subprocess_run.return_value = mock_stdout
    result = dbt_platform_helper.utils.git.git_remote()
    assert result == "testorg/testrepo"


@patch("subprocess.run")
def test_check_if_commit_exists_success(mock_run):
    mock_result = Mock()
    mock_result.stdout = b"origin/my-branch"
    mock_result.stderr = None
    mock_run.return_value = mock_result
    dbt_platform_helper.utils.git.check_if_commit_exists("1234")


@patch("subprocess.run")
def test_check_if_commit_exists_raises_platform_exception_if_no_commit_found(mock_run):
    mock_result = Mock()
    mock_result.stdout = None
    mock_result.stderr = b"no such commit 1234"
    mock_run.return_value = mock_result
    with pytest.raises(PlatformException):
        dbt_platform_helper.utils.git.check_if_commit_exists("1234")
