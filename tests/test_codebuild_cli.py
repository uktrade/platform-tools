import json
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
from commands.codebuild_cli import check_git_url
from commands.codebuild_cli import check_service_role
from commands.codebuild_cli import create_codedeploy_role
from commands.codebuild_cli import link_github
from commands.codebuild_cli import slackcreds
from commands.codebuild_cli import update_parameter


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    moto_credentials_file_path = Path(__file__).parent.absolute() / "dummy_aws_credentials"
    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = str(moto_credentials_file_path)


@pytest.fixture
def alias_session(aws_credentials):
    with mock_iam():
        session = boto3.session.Session(region_name="eu-west-2")
        session.client("iam").create_account_alias(AccountAlias="foo")

        yield session


# Not much value in testing these while moto doesn't support `import_source_credentials`` or `list_source_credentials`
# def test_import_pat():
#     ...
# def test_check_github_conn():
#     ...


@mock_iam
def test_check_service_role_does_not_exist(capfd, aws_credentials):
    """Test that check_service_role outputs expects error method when codebuild
    role does not exist."""

    session = boto3.session.Session(profile_name="foo")
    with pytest.raises(SystemExit):
        check_service_role(session)
    out, _ = capfd.readouterr()

    assert "Role for service does not exist; run ./codebuild_cli.py create-codeploy-role\n" in out


@mock_iam
def test_check_service_role_returns_role_arn():
    """Test that check_service_role returns an arn string containing account
    number and role name."""

    session = boto3.session.Session()
    client = session.client("iam")
    client.create_role(
        RoleName="ci-CodeBuild-role",
        AssumeRolePolicyDocument="123",
    )

    assert check_service_role(session) == "arn:aws:iam::123456789012:role/ci-CodeBuild-role"


@mock_ssm
def test_update_parameter():
    """Test that update_paramater creates a parameter with expected Name and
    Value values where none exists."""

    session = boto3.session.Session(region_name="eu-west-2")
    assert update_parameter(session, "name", "description", "value") == None

    response = session.client("ssm").get_parameter(Name="name")
    parameter = response["Parameter"]

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert parameter["Name"] == "name"
    assert parameter["Value"] == "kms:alias/aws/ssm:value"


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://github.com/uktrade/digital-workspace", "https://github.com/uktrade/digital-workspace"),
        ("git@github.com:uktrade/digital-workspace", "https://github.com/uktrade/digital-workspace"),
    ],
)
def test_check_git_url_valid(url, expected):
    """Test that check_git_url returns unmodified url string when url is
    valid."""

    assert check_git_url(url) == expected


@pytest.mark.parametrize("url", ["http://github.com/uktrade/digital-workspace", "not-a-url-tbh"])
def test_check_git_url_invalid(url, capfd):
    """Test that check_git_url prints an error when url is invalid."""

    with pytest.raises(SystemExit):
        check_git_url(url)

    out, _ = capfd.readouterr()
    
    assert (
        "Unable to recognise Git URL format, make sure it is either:\nhttps://github.com/<org>/<repository-name>\ngit@github.com:<org>/<repository-name>\n"
        in out
    )


@patch("commands.codebuild_cli.import_pat")
@mock_sts
@mock_codebuild
def test_link_github(import_pat, alias_session):
    """Test that link_github calls import_pat."""
    runner = CliRunner()
    runner.invoke(link_github, ["--pat", "123", "--project-profile", "foo"])

    import_pat.assert_called_once()


@mock_sts
def test_create_codedeploy_role_returns_200(alias_session):
    runner = CliRunner()
    result = runner.invoke(create_codedeploy_role, ["--project-profile", "foo"])
    response = alias_session.client("iam", region_name=AWS_REGION).get_role(RoleName="ci-CodeBuild-role")[
       "ResponseMetadata"
    ]
    policy = alias_session.client("iam", region_name=AWS_REGION).list_attached_role_policies(
        RoleName="ci-CodeBuild-role",
    )["AttachedPolicies"][0]

    assert "Policy created" in result.output
    assert "Role created" in result.output
    assert "Policy attached to Role" in result.output
    assert response["HTTPStatusCode"] == 200
    assert policy["PolicyName"] == "ci-CodeBuild-policy"


@mock_sts
def test_create_codedeploy_role_policy_already_exists(alias_session):
    current_filepath = os.path.dirname(os.path.realpath(__file__))
    with open(f"{current_filepath}/../templates/put-codebuild-role-policy.json") as f:
        policy_doc = json.load(f)
    alias_session.client("iam", region_name=AWS_REGION).create_policy(
        PolicyName="ci-CodeBuild-policy",
        PolicyDocument=json.dumps(policy_doc),
        Description="Custom Policy for codebuild",
        Tags=[
            {"Key": "Name", "Value": "CustomPolicy"},
        ],
    )
    runner = CliRunner()
    result = runner.invoke(create_codedeploy_role, ["--project-profile", "foo"], input="y")

    assert "Policy updated" in result.output

    account_id = alias_session.client("sts").get_caller_identity().get("Account")
    versions = alias_session.client("iam").list_policy_versions(
        PolicyArn=f"arn:aws:iam::{account_id}:policy/ci-CodeBuild-policy",
    )["Versions"]

    assert len(versions) == 2
    assert versions[0]["VersionId"] == "v1"
    assert versions[0]["IsDefaultVersion"] == False
    assert versions[1]["VersionId"] == "v2"
    assert versions[1]["IsDefaultVersion"] == True


@mock_sts
def test_create_codedeploy_role_limit_exceeded_exception(alias_session):
    runner = CliRunner()
    for i in range(6):
        result = runner.invoke(create_codedeploy_role, ["--project-profile", "foo"], input="y")

    assert (
        "You have hit the limit of max managed policies, please delete an existing version and try again"
        in result.output
    )


# Commented out while we investigate potential bug - `create_project` wants a service role arn passed as an argument and we are passing it a non-service role arn
# https://uktrade.atlassian.net/browse/DBTP-184

# @patch("commands.codebuild_cli.check_github_conn")
# @mock_sts
# @mock_iam
# @mock_codebuild
# def test_codedeploy(check_github_conn, aws_credentials):
#     session = boto3.session.Session()
#     session.client("iam").create_account_alias(AccountAlias="foo")
#     runner = CliRunner()
#     runner.invoke(create_codedeploy_role, ["--project-profile", "foo"])
#     result = runner.invoke(codedeploy, ["--name", "unit-test-project", "--git", "https://github.com/uktrade/not-a-real-repo", "--branch", "main", "--buildspec", "./buildspec.yml", "--project-profile", "foo" ])

#     assert "Codebuild project unit-test-project created" in result.output


@mock_ssm
@mock_sts
def test_slackcreds(alias_session):
    runner = CliRunner()
    result = runner.invoke(
        slackcreds,
        ["--workspace", "workspace", "--channel", "channel", "--token", "token", "--project-profile", "foo"],
        input="y",
    )

    assert "Paramater Store updated" in result.output

    SLACK = {
        "workspace": {
            "name": "/codebuild/slack_workspace_id",
            "description": "Slack Workspace ID",
            "value": "workspace",
        },
        "channel": {"name": "/codebuild/slack_channel_id", "description": "Slack Channel ID", "value": "channel"},
        "token": {"name": "/codebuild/slack_api_token", "description": "Slack API Token", "value": "token"},
    }
    for item, value in SLACK.items():
        response = alias_session.client("ssm").get_parameter(Name=SLACK[item]["name"])
        parameter = response["Parameter"]

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        value = SLACK[item]["value"]
        assert parameter["Value"] == f"kms:alias/aws/ssm:{value}"
