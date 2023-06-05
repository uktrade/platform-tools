import os
from pathlib import Path
from unittest.mock import patch

import boto3
import pytest
from click.testing import CliRunner
from moto import mock_codebuild
from moto import mock_iam
from moto import mock_ssm
from moto import mock_sts

from commands.codebuild_cli import AWS_REGION
from commands.codebuild_cli import check_git_url, link_github
from commands.codebuild_cli import check_service_role
from commands.codebuild_cli import update_parameter
from utils.aws import check_aws_conn

@pytest.fixture(scope='module')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    moto_credentials_file_path = Path(__file__).parent.absolute() / 'dummy_aws_credentials'
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = str(moto_credentials_file_path)

# Not much value in testing these while moto doesn't support `import_source_credentials`` or `list_source_credentials`
def test_import_pat():
    ...
def test_check_github_conn():
    ...


@mock_iam
def test_check_service_role_does_not_exist(capfd, aws_credentials):
    session = boto3.session.Session(profile_name="foo")
    with pytest.raises(SystemExit):
        check_service_role(session)
    out, _ = capfd.readouterr()
   
    assert "Role for service does not exist run ./codebuild_cli.py create-codeploy-role" in out


@mock_iam
def test_check_service_role_returns_role_arn():
    session = boto3.session.Session()
    client = session.client("iam")
    client.create_role(
        RoleName='ci-CodeBuild-role',
        AssumeRolePolicyDocument='123',
    )
    
    assert check_service_role(session) == "arn:aws:iam::123456789012:role/ci-CodeBuild-role"


@mock_ssm
def test_update_parameter():
    session = boto3.session.Session()
    assert update_parameter(session, "name", "description", "value" ) == None
    
    response = session.client("ssm").get_parameter(Name="name")
    parameter = response["Parameter"]
    
    assert response['ResponseMetadata']["HTTPStatusCode"] == 200
    assert parameter["Name"] == "name"
    assert parameter["Value"] == "kms:alias/aws/ssm:value"


@pytest.mark.parametrize("url,expected", [("https://github.com/uktrade/digital-workspace","https://github.com/uktrade/digital-workspace"), ("git@github.com:uktrade/digital-workspace", "https://github.com/uktrade/digital-workspace")])
def test_check_git_url_valid(url, expected):
    assert check_git_url(url) == expected

@pytest.mark.parametrize("url", ["http://github.com/uktrade/digital-workspace", "not-a-url-tbh"])
def test_check_git_url_invalid(url, capfd):
    with pytest.raises(SystemExit):
        check_git_url(url)
    
    out, _ = capfd.readouterr()
    
    assert "Unable to recognise git url format, make sure its either:\n            https://github.com/<org>/<repository-name>\n            git@github.com:<org>/<repository-name>\n            \n" in out

@patch("commands.codebuild_cli.import_pat")
@mock_sts
@mock_iam
@mock_codebuild
def test_link_github(import_pat, aws_credentials):
    session = boto3.session.Session()
    session.client("iam").create_account_alias(AccountAlias="foo")
    runner = CliRunner()
    result = runner.invoke(link_github, ["--pat", "123", "--project-profile", "foo"])
    
    import_pat.assert_called_once()
     