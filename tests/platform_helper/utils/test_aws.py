from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import boto3
import botocore
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from dbt_platform_helper.constants import REFRESH_TOKEN_MESSAGE
from dbt_platform_helper.providers.aws.exceptions import (
    CopilotCodebaseNotFoundException,
)
from dbt_platform_helper.providers.aws.exceptions import LogGroupNotFoundException
from dbt_platform_helper.providers.validation import ValidationException
from dbt_platform_helper.utils.aws import NoProfileForAccountIdException
from dbt_platform_helper.utils.aws import check_codebase_exists
from dbt_platform_helper.utils.aws import get_account_details
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.aws import get_build_url_from_pipeline_execution_id
from dbt_platform_helper.utils.aws import get_codestar_connection_arn
from dbt_platform_helper.utils.aws import get_connection_string
from dbt_platform_helper.utils.aws import get_image_build_project
from dbt_platform_helper.utils.aws import get_manual_release_pipeline
from dbt_platform_helper.utils.aws import (
    get_postgres_connection_data_updated_with_master_secret,
)
from dbt_platform_helper.utils.aws import get_profile_name_from_account_id
from dbt_platform_helper.utils.aws import get_public_repository_arn
from dbt_platform_helper.utils.aws import get_ssm_secrets
from dbt_platform_helper.utils.aws import set_ssm_param
from dbt_platform_helper.utils.aws import wait_for_log_group_to_exist
from tests.platform_helper.conftest import mock_aws_client
from tests.platform_helper.conftest import mock_codestar_connections_boto_client
from tests.platform_helper.conftest import mock_ecr_public_repositories_boto_client
from tests.platform_helper.conftest import mock_get_caller_identity


def test_get_aws_session_or_abort_profile_not_configured(clear_session_cache, capsys):
    with pytest.raises(SystemExit):
        get_aws_session_or_abort("foo")

    captured = capsys.readouterr()

    assert """AWS profile "foo" is not configured.""" in captured.out


def get_mock_session(name):
    session = Mock(name=name)
    client = Mock(name=f"client-mock-for-{name}")
    session.client.return_value = client
    client.get_caller_identity.return_value = {"Account": "account", "UserId": "user"}
    client.list_account_aliases.return_value = {"AccountAliases": "account", "UserId": "user"}

    return session


@patch("boto3.session.Session")
def test_get_aws_session_caches_sessions_per_profile(mock_session):
    mock_session.side_effect = (get_mock_session("one"), get_mock_session("two"))
    session1 = get_aws_session_or_abort()
    session2 = get_aws_session_or_abort()

    session3 = get_aws_session_or_abort("my-profile")
    session4 = get_aws_session_or_abort("my-profile")

    assert session1 is session2
    assert session3 is session4
    assert session1 is not session4


@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
def test_get_ssm_secrets(mock_get_aws_session_or_abort):
    client = mock_aws_client(mock_get_aws_session_or_abort)
    client.get_parameters_by_path.return_value = {
        "Parameters": [
            {
                "Name": "/copilot/test-application/development/secrets/TEST_SECRET",
                "Description": "A test parameter",
                "Value": "test value",
                "Type": "SecureString",
            }
        ]
    }

    result = get_ssm_secrets("test-application", "development")

    assert result == [("/copilot/test-application/development/secrets/TEST_SECRET", "test value")]


@pytest.mark.parametrize(
    "aws_profile, side_effect, expected_error_message",
    [
        (
            "existing_profile",
            botocore.exceptions.NoCredentialsError(
                error_msg="There are no credentials set for this session."
            ),
            f"There are no credentials set for this session. {REFRESH_TOKEN_MESSAGE}",
        ),
        (
            "existing_profile",
            botocore.exceptions.UnauthorizedSSOTokenError(
                error_msg="The SSO Token used for this session is unauthorised."
            ),
            f"The SSO Token used for this session is unauthorised. {REFRESH_TOKEN_MESSAGE}",
        ),
        (
            "existing_profile",
            botocore.exceptions.TokenRetrievalError(
                error_msg="Unable to retrieve the Token for this session.", provider="sso"
            ),
            f"Unable to retrieve the Token for this session. {REFRESH_TOKEN_MESSAGE}",
        ),
        (
            "existing_profile",
            botocore.exceptions.SSOTokenLoadError(
                error_msg="The SSO session associated with this profile has expired, is not set or is otherwise invalid."
            ),
            f"The SSO session associated with this profile has expired, is not set or is otherwise invalid. {REFRESH_TOKEN_MESSAGE}",
        ),
    ],
)
@patch("dbt_platform_helper.utils.aws.get_account_details")
@patch("boto3.session.Session")
@patch("click.secho")
def test_get_aws_session_or_abort_errors(
    mock_secho,
    mock_session,
    mock_get_account_details,
    aws_profile,
    side_effect,
    expected_error_message,
):
    if isinstance(side_effect, botocore.exceptions.ProfileNotFound):
        mock_session.side_effect = side_effect
    else:
        mock_get_account_details.side_effect = side_effect

    with pytest.raises(SystemExit) as exc_info:
        get_aws_session_or_abort(aws_profile=aws_profile)

    assert exc_info.value.code == 1
    assert mock_secho.call_count > 0
    assert mock_secho.call_args[0][0] == expected_error_message


@patch("boto3.session.Session")
@patch("click.secho")
def test_get_aws_session_or_abort_with_misconfigured_profile(mock_secho, mock_session):
    misconfigured_profile = "nonexistent_profile"
    expected_error_message = f"""AWS profile "{misconfigured_profile}" is not configured."""
    mock_session.side_effect = botocore.exceptions.ProfileNotFound(profile=misconfigured_profile)

    with pytest.raises(SystemExit) as exc_info:
        get_aws_session_or_abort(aws_profile=misconfigured_profile)

    assert exc_info.value.code == 1
    assert mock_secho.call_count > 0
    assert mock_secho.call_args[0][0] == expected_error_message


@pytest.mark.parametrize(
    "overwrite, exists",
    [(False, False), (False, True)],
)
@mock_aws
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
def test_set_ssm_param(mock_get_aws_session_or_abort, overwrite, exists):
    mocked_ssm = boto3.client("ssm")
    mock_aws_client(mock_get_aws_session_or_abort, mocked_ssm)

    set_ssm_param(
        "test-application",
        "development",
        "/copilot/test-application/development/secrets/TEST_SECRET",
        "random value",
        overwrite,
        exists,
        "Created for testing purposes.",
    )

    params = dict(
        Path="/copilot/test-application/development/secrets/",
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    result = mocked_ssm.get_parameters_by_path(**params)["Parameters"][0]

    expected_response = {
        "ARN": "arn:aws:ssm:eu-west-2:123456789012:parameter/copilot/test-application/development/secrets/TEST_SECRET",
        "Name": "/copilot/test-application/development/secrets/TEST_SECRET",
        "Type": "SecureString",
        "Value": "random value",
    }

    # assert result is a superset of expected_response
    assert result.items() >= expected_response.items()


@mock_aws
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
def test_set_ssm_param_with_existing_secret(mock_get_aws_session_or_abort):
    mocked_ssm = boto3.client("ssm")
    mock_aws_client(mock_get_aws_session_or_abort, mocked_ssm)

    mocked_ssm.put_parameter(
        Name="/copilot/test-application/development/secrets/TEST_SECRET",
        Description="A test parameter",
        Value="test value",
        Type="SecureString",
    )

    params = dict(
        Path="/copilot/test-application/development/secrets/",
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    assert mocked_ssm.get_parameters_by_path(**params)["Parameters"][0]["Value"] == "test value"

    set_ssm_param(
        "test-application",
        "development",
        "/copilot/test-application/development/secrets/TEST_SECRET",
        "overwritten value",
        True,
        True,
        "Created for testing purposes.",
    )

    result = mocked_ssm.get_parameters_by_path(**params)["Parameters"][0]["Value"]

    assert result != "test value"
    assert result == "overwritten value"


@mock_aws
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
def test_set_ssm_param_with_overwrite_but_not_exists(mock_get_aws_session_or_abort):
    mocked_ssm = boto3.client("ssm")
    mock_aws_client(mock_get_aws_session_or_abort, mocked_ssm)

    mocked_ssm.put_parameter(
        Name="/copilot/test-application/development/secrets/TEST_SECRET",
        Description="A test parameter",
        Value="test value",
        Type="SecureString",
    )

    params = dict(
        Path="/copilot/test-application/development/secrets/",
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    assert mocked_ssm.get_parameters_by_path(**params)["Parameters"][0]["Value"] == "test value"

    with pytest.raises(ValidationException) as exception:
        set_ssm_param(
            "test-application",
            "development",
            "/copilot/test-application/development/secrets/TEST_SECRET",
            "overwritten value",
            True,
            False,
            "Created for testing purposes.",
        )

    assert (
        """Arguments "overwrite" is set to True, but "exists" is set to False."""
        == exception.value.args[0]
    )


@mock_aws
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
def test_set_ssm_param_tags(mock_get_aws_session_or_abort):
    mocked_ssm = boto3.client("ssm")
    mock_aws_client(mock_get_aws_session_or_abort, mocked_ssm)

    set_ssm_param(
        "test-application",
        "development",
        "/copilot/test-application/development/secrets/TEST_SECRET",
        "random value",
        False,
        False,
        "Created for testing purposes.",
    )

    parameters = mocked_ssm.describe_parameters(
        ParameterFilters=[
            {"Key": "tag:copilot-application", "Values": ["test-application"]},
            {"Key": "tag:copilot-environment", "Values": ["development"]},
        ]
    )["Parameters"]

    assert len(parameters) == 1
    assert parameters[0]["Name"] == "/copilot/test-application/development/secrets/TEST_SECRET"

    response = mocked_ssm.describe_parameters(ParameterFilters=[{"Key": "tag:copilot-application"}])

    assert len(response["Parameters"]) == 1
    assert {parameter["Name"] for parameter in response["Parameters"]} == {
        "/copilot/test-application/development/secrets/TEST_SECRET"
    }


@mock_aws
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
def test_set_ssm_param_tags_with_existing_secret(mock_get_aws_session_or_abort):
    mocked_ssm = boto3.client("ssm")
    mock_aws_client(mock_get_aws_session_or_abort, mocked_ssm)

    secret_name = "/copilot/test-application/development/secrets/TEST_SECRET"
    tags = [
        {"Key": "copilot-application", "Value": "test-application"},
        {"Key": "copilot-environment", "Value": "development"},
    ]

    mocked_ssm.put_parameter(
        Name=secret_name,
        Description="A test parameter",
        Value="test value",
        Type="SecureString",
        Tags=tags,
    )

    assert (
        tags
        == mocked_ssm.list_tags_for_resource(ResourceType="Parameter", ResourceId=secret_name)[
            "TagList"
        ]
    )

    set_ssm_param(
        "test-application",
        "development",
        secret_name,
        "random value",
        True,
        True,
        "Created for testing purposes.",
    )

    assert (
        tags
        == mocked_ssm.list_tags_for_resource(ResourceType="Parameter", ResourceId=secret_name)[
            "TagList"
        ]
    )


@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@pytest.mark.parametrize(
    "connection_names, app_name, expected_arn",
    [
        [
            [
                "test-app-name",
            ],
            "test-app-name",
            f"arn:aws:codestar-connections:eu-west-2:1234567:connection/test-app-name",
        ],
        [
            [
                "test-app-name-1",
                "test-app-name-2",
                "test-app-name-3",
            ],
            "test-app-name-2",
            f"arn:aws:codestar-connections:eu-west-2:1234567:connection/test-app-name-2",
        ],
        [
            [
                "test-app-name",
            ],
            "test-app-name-2",
            None,
        ],
    ],
)
def test_get_codestar_connection_arn(
    mock_get_aws_session_or_abort, connection_names, app_name, expected_arn
):
    mock_codestar_connections_boto_client(mock_get_aws_session_or_abort, connection_names)

    result = get_codestar_connection_arn(app_name)

    assert result == expected_arn


@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@pytest.mark.parametrize(
    "repository_uri, expected_arn",
    [
        ("public.ecr.aws/abc123/my/app", "arn:aws:ecr-public::000000000000:repository/my/app"),
        ("public.ecr.aws/abc123/my/app2", "arn:aws:ecr-public::000000000000:repository/my/app2"),
        ("public.ecr.aws/abc123/does-not/exist", None),
    ],
)
def test_get_public_repository_arn(mock_get_aws_session_or_abort, repository_uri, expected_arn):
    mock_ecr_public_repositories_boto_client(mock_get_aws_session_or_abort)

    result = get_public_repository_arn(repository_uri)

    assert result == expected_arn


@mock_aws
def test_check_codebase_exists(mock_application):
    mock_application.environments["development"].session.client("ssm")
    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name="/copilot/applications/test-application/codebases/application",
        Type="String",
        Value="""
                                             {
                                                "name": "test-app", 
                                                "repository": "uktrade/test-app",
                                                "services": "1234"
                                             }
                                        """,
    )

    check_codebase_exists(
        mock_application.environments["development"].session, mock_application, "application"
    )


@mock_aws
def test_check_codebase_does_not_exist(mock_application):
    mock_application.environments["development"].session.client("ssm")
    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name="/copilot/applications/test-application/codebases/application",
        Type="String",
        Value="""
                                             {
                                                "name": "test-app", 
                                                "repository": "uktrade/test-app",
                                                "services": "1234"
                                             }
                                        """,
    )

    with pytest.raises(CopilotCodebaseNotFoundException):
        check_codebase_exists(
            mock_application.environments["development"].session,
            mock_application,
            "not-found-application",
        )


@mock_aws
def test_check_codebase_errors_when_json_is_malformed(mock_application):
    mock_application.environments["development"].session.client("ssm")
    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name="/copilot/applications/test-application/codebases/application",
        Type="String",
        Value="not valid JSON",
    )

    with pytest.raises(CopilotCodebaseNotFoundException):
        check_codebase_exists(
            mock_application.environments["development"].session, mock_application, "application"
        )


@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
def test_get_account_id(mock_get_aws_session_or_abort):
    mock_get_caller_identity(mock_get_aws_session_or_abort)

    account_id, user_id = get_account_details()

    assert account_id == "000000000000"
    assert user_id == "abc123"


def test_get_account_id_passing_in_client():
    mock_client = MagicMock()
    mock_client.get_caller_identity.return_value = {"Account": "000000000001", "UserId": "abc456"}

    account_id, user_id = get_account_details(mock_client)

    assert account_id == "000000000001"
    assert user_id == "abc456"


def test_get_profile_name_from_account_id(fakefs):
    assert get_profile_name_from_account_id("000000000") == "development"
    assert get_profile_name_from_account_id("111111111") == "staging"
    assert get_profile_name_from_account_id("222222222") == "production"


def test_get_profile_name_from_account_id_when_not_using_sso(fs):
    fs.create_file(
        Path.home().joinpath(".aws/config"),
        contents="""
[profile development]
region = eu-west-2
output = json
profile_account_id = 123456789

[profile staging]
region = eu-west-2
output = json
profile_account_id = 987654321
""",
    )
    assert get_profile_name_from_account_id("123456789") == "development"
    assert get_profile_name_from_account_id("987654321") == "staging"


def test_get_profile_name_from_account_id_with_no_matching_account(fakefs):
    with pytest.raises(NoProfileForAccountIdException) as error:
        get_profile_name_from_account_id("999999999")

    assert str(error.value) == "No profile found for account 999999999"


@mock_aws
def test_update_postgres_parameter_with_master_secret():
    session = boto3.session.Session()
    parameter_name = "test-parameter"
    session.client("ssm").put_parameter(
        Name=parameter_name,
        Value='{"username": "read-only-user", "password": ">G12345", "host": "test.com", "port": 5432}',
        Type="String",
    )
    secret_arn = session.client("secretsmanager").create_secret(
        Name="master-secret", SecretString='{"username": "postgres", "password": ">G6789"}'
    )["ARN"]

    updated_parameter_value = get_postgres_connection_data_updated_with_master_secret(
        session, parameter_name, secret_arn
    )

    assert updated_parameter_value == {
        "username": "postgres",
        "password": "%3EG6789",
        "host": "test.com",
        "port": 5432,
    }


@mock_aws
def test_get_connection_string():
    db_identifier = f"my_app-my_env-my_postgres"
    session = boto3.session.Session()
    master_secret_arn = "arn://the-rds-master-arn"
    master_secret_arn_param = "/copilot/my_app/my_env/secrets/MY_POSTGRES_RDS_MASTER_ARN"
    session.client("ssm").put_parameter(
        Name=master_secret_arn_param,
        Value=master_secret_arn,
        Type="String",
    )
    mock_connection_data = Mock(
        return_value={
            "username": "master_user",
            "password": "master_password",
            "host": "hostname",
            "port": "1234",
            "dbname": "main",
        }
    )

    connection_string = get_connection_string(
        session, "my_app", "my_env", db_identifier, connection_data=mock_connection_data
    )

    mock_connection_data.assert_called_once_with(
        session, f"/copilot/my_app/my_env/secrets/MY_POSTGRES_READ_ONLY_USER", master_secret_arn
    )
    assert (
        connection_string
        == "postgres://master_user:master_password@hostname:1234/main"  # trufflehog:ignore
    )


class ObjectWithId:
    def __init__(self, id, tags=None):
        self.id = id
        self.tags = tags


def describe_subnet_object(subnet_id: str, visibility: str):
    return {
        "SubnetId": subnet_id,
        "Tags": [{"Key": "subnet_type", "Value": visibility}],
    }


def describe_security_group_object(vpc_id: str, sg_id: str, name: str):
    return {
        "GroupId": sg_id,
        "Tags": [
            {"Key": "Name", "Value": name},
        ],
        "VpcId": vpc_id,
    }


def mock_vpc_info_session():
    mock_session = Mock()
    mock_client = Mock()
    mock_session.client.return_value = mock_client
    vpc_data = {"Vpcs": [{"VpcId": "vpc-123456"}]}
    mock_client.describe_vpcs.return_value = vpc_data

    mock_vpc = Mock()

    mock_client.describe_subnets.return_value = {
        "Subnets": [
            describe_subnet_object("subnet-public-1", "public"),
            describe_subnet_object("subnet-public-2", "public"),
            describe_subnet_object("subnet-private-1", "private"),
            describe_subnet_object("subnet-private-2", "private"),
        ]
    }

    mock_client.describe_security_groups.return_value = {
        "SecurityGroups": [
            describe_security_group_object("vpc-123456", "sg-abc123", "copilot-my_app-my_env-env"),
        ]
    }

    sec_groups = Mock()
    mock_vpc.security_groups = sec_groups
    sec_groups.all.return_value = [
        ObjectWithId("sg-abc345", tags=[]),
        ObjectWithId("sg-abc567", tags=[{"Key": "Name", "Value": "copilot-other_app-my_env-env"}]),
        ObjectWithId(
            "sg-abc123", tags=[{"Key": "Name", "Value": "copilot-my_app-my_env-env"}]
        ),  # this is the correct one.
        ObjectWithId("sg-abc456"),
        ObjectWithId("sg-abc678", tags=[{"Key": "Name", "Value": "copilot-my_app-other_env-env"}]),
    ]

    return mock_session, mock_client, mock_vpc


def test_wait_for_log_group_to_exist_success():
    log_group_name = "/ecs/test-log-group"
    mock_client = Mock()
    mock_client.describe_log_groups.return_value = {"logGroups": [{"logGroupName": log_group_name}]}

    wait_for_log_group_to_exist(mock_client, log_group_name)


def test_wait_for_log_group_to_exist_fails_when_log_group_not_found():
    log_group_name = "/ecs/test-log-group"
    mock_client = Mock()
    mock_client.describe_log_groups.return_value = {"logGroups": [{"logGroupName": log_group_name}]}

    with pytest.raises(LogGroupNotFoundException, match=f'No log group called "not_found"'):
        wait_for_log_group_to_exist(mock_client, "not_found", 1)


@pytest.mark.parametrize(
    "execution_id, pipeline_name, expected_url",
    [
        (
            "12345678-1234-1234-1234-123456789012",
            "my-pipeline",
            "https://eu-west-2.console.aws.amazon.com/codesuite/codepipeline/pipelines/my-pipeline/executions/12345678-1234-1234-1234-123456789012",
        ),
        (
            "",
            "my-pipeline",
            "https://eu-west-2.console.aws.amazon.com/codesuite/codepipeline/pipelines/my-pipeline/executions/",
        ),
        (
            "12345678-1234-1234-1234-123456789012",
            "",
            "https://eu-west-2.console.aws.amazon.com/codesuite/codepipeline/pipelines//executions/12345678-1234-1234-1234-123456789012",
        ),
    ],
)
def test_get_build_url_from_pipeline_execution_id(execution_id, pipeline_name, expected_url):
    result = get_build_url_from_pipeline_execution_id(execution_id, pipeline_name)
    assert result == expected_url


@pytest.mark.parametrize(
    "new_build_project_name_exists, expected_build_project_name",
    [
        (
            False,
            "test-application-test-codebase-codebase-pipeline-image-build",
        ),
        (
            True,
            "test-application-test-codebase-codebase-image-build",
        ),
    ],
)
def test_get_image_build_project(new_build_project_name_exists, expected_build_project_name):
    mock_client = Mock()

    if new_build_project_name_exists is False:
        mock_client.batch_get_projects.return_value = {"projects": []}

    result = get_image_build_project(mock_client, "test-application", "test-codebase")

    assert result == expected_build_project_name


@pytest.mark.parametrize(
    "new_pipeline_name_exists, expected_pipeline_name",
    [
        (
            False,
            "test-application-test-codebase-manual-release-pipeline",
        ),
        (
            True,
            "test-application-test-codebase-manual-release",
        ),
    ],
)
def test_get_manual_release_pipeline(new_pipeline_name_exists, expected_pipeline_name):
    mock_client = Mock()

    if new_pipeline_name_exists is False:
        mock_client.get_pipeline.side_effect = ClientError(
            {"Error": {"Code": "PipelineNotFoundException", "Message": "Pipeline not found"}},
            "get_pipeline",
        )

    result = get_manual_release_pipeline(mock_client, "test-application", "test-codebase")

    assert result == expected_pipeline_name
