from unittest.mock import Mock
from unittest.mock import patch

import dbt_platform_helper.utils.git


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
