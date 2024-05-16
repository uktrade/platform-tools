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
