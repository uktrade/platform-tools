import json
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import mock_open
from unittest.mock import patch

import boto3
import botocore
import pytest
from moto import mock_aws

from dbt_platform_helper.providers.aws import AWSException
from dbt_platform_helper.providers.aws import CopilotCodebaseNotFoundException
from dbt_platform_helper.providers.aws import LogGroupNotFoundException
from dbt_platform_helper.providers.validation import ValidationException
from dbt_platform_helper.utils.aws import NoProfileForAccountIdException
from dbt_platform_helper.utils.aws import Vpc
from dbt_platform_helper.utils.aws import check_codebase_exists
from dbt_platform_helper.utils.aws import get_account_details
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.aws import get_codestar_connection_arn
from dbt_platform_helper.utils.aws import get_connection_string
from dbt_platform_helper.utils.aws import get_load_balancer_domain_and_configuration
from dbt_platform_helper.utils.aws import (
    get_postgres_connection_data_updated_with_master_secret,
)
from dbt_platform_helper.utils.aws import get_profile_name_from_account_id
from dbt_platform_helper.utils.aws import get_public_repository_arn
from dbt_platform_helper.utils.aws import get_ssm_secrets
from dbt_platform_helper.utils.aws import get_supported_opensearch_versions
from dbt_platform_helper.utils.aws import get_supported_redis_versions
from dbt_platform_helper.utils.aws import get_vpc_info_by_name
from dbt_platform_helper.utils.aws import set_ssm_param
from dbt_platform_helper.utils.aws import wait_for_log_group_to_exist
from tests.platform_helper.conftest import mock_aws_client
from tests.platform_helper.conftest import mock_codestar_connections_boto_client
from tests.platform_helper.conftest import mock_ecr_public_repositories_boto_client
from tests.platform_helper.conftest import mock_get_caller_identity

HYPHENATED_APPLICATION_NAME = "hyphenated-application-name"
ALPHANUMERIC_ENVIRONMENT_NAME = "alphanumericenvironmentname123"
ALPHANUMERIC_SERVICE_NAME = "alphanumericservicename123"
COPILOT_IDENTIFIER = "c0PIlotiD3ntIF3r"
CLUSTER_NAME_SUFFIX = f"Cluster-{COPILOT_IDENTIFIER}"
SERVICE_NAME_SUFFIX = f"Service-{COPILOT_IDENTIFIER}"
REFRESH_TOKEN_MESSAGE = (
    "To refresh this SSO session run `aws sso login` with the corresponding profile"
)


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
def test_get_load_balancer_domain_and_configuration_no_clusters(capfd):
    with pytest.raises(SystemExit):
        get_load_balancer_domain_and_configuration(
            boto3.Session(),
            HYPHENATED_APPLICATION_NAME,
            ALPHANUMERIC_ENVIRONMENT_NAME,
            ALPHANUMERIC_SERVICE_NAME,
        )

    out, _ = capfd.readouterr()

    assert (
        out == f"There are no clusters for environment {ALPHANUMERIC_ENVIRONMENT_NAME} of "
        f"application {HYPHENATED_APPLICATION_NAME} in AWS account default\n"
    )


@mock_aws
def test_get_load_balancer_domain_and_configuration_no_services(capfd):
    boto3.Session().client("ecs").create_cluster(
        clusterName=f"{HYPHENATED_APPLICATION_NAME}-{ALPHANUMERIC_ENVIRONMENT_NAME}-{CLUSTER_NAME_SUFFIX}"
    )
    with pytest.raises(SystemExit):
        get_load_balancer_domain_and_configuration(
            boto3.Session(),
            HYPHENATED_APPLICATION_NAME,
            ALPHANUMERIC_ENVIRONMENT_NAME,
            ALPHANUMERIC_SERVICE_NAME,
        )

    out, _ = capfd.readouterr()

    assert (
        out == f"There are no services called {ALPHANUMERIC_SERVICE_NAME} for environment "
        f"{ALPHANUMERIC_ENVIRONMENT_NAME} of application {HYPHENATED_APPLICATION_NAME} "
        f"in AWS account default\n"
    )


@mock_aws
@pytest.mark.parametrize(
    "svc_name",
    [
        ALPHANUMERIC_SERVICE_NAME,
        "test",
        "test-service",
        "test-service-name",
    ],
)
def test_get_load_balancer_domain_and_configuration(tmp_path, svc_name):
    cluster_name = (
        f"{HYPHENATED_APPLICATION_NAME}-{ALPHANUMERIC_ENVIRONMENT_NAME}-{CLUSTER_NAME_SUFFIX}"
    )
    service_name = f"{HYPHENATED_APPLICATION_NAME}-{ALPHANUMERIC_ENVIRONMENT_NAME}-{svc_name}-{SERVICE_NAME_SUFFIX}"
    session = boto3.Session()
    mocked_vpc_id = session.client("ec2").create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    mocked_subnet_id = session.client("ec2").create_subnet(
        VpcId=mocked_vpc_id, CidrBlock="10.0.0.0/16"
    )["Subnet"]["SubnetId"]
    mocked_elbv2_client = session.client("elbv2")
    mocked_load_balancer_arn = mocked_elbv2_client.create_load_balancer(
        Name="foo", Subnets=[mocked_subnet_id]
    )["LoadBalancers"][0]["LoadBalancerArn"]
    target_group = mocked_elbv2_client.create_target_group(
        Name="foo", Protocol="HTTPS", Port=80, VpcId=mocked_vpc_id
    )
    target_group_arn = target_group["TargetGroups"][0]["TargetGroupArn"]
    mocked_elbv2_client.create_listener(
        LoadBalancerArn=mocked_load_balancer_arn,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )
    mocked_ecs_client = session.client("ecs")
    mocked_ecs_client.create_cluster(clusterName=cluster_name)
    mocked_ecs_client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        loadBalancers=[{"loadBalancerName": "foo", "targetGroupArn": target_group_arn}],
    )
    mocked_service_manifest_contents = {
        "environments": {ALPHANUMERIC_ENVIRONMENT_NAME: {"http": {"alias": "somedomain.tld"}}}
    }
    open_mock = mock_open(read_data=json.dumps(mocked_service_manifest_contents))

    with patch("dbt_platform_helper.utils.aws.open", open_mock):
        domain_name, load_balancer_configuration = get_load_balancer_domain_and_configuration(
            boto3.Session(), HYPHENATED_APPLICATION_NAME, ALPHANUMERIC_ENVIRONMENT_NAME, svc_name
        )

    open_mock.assert_called_once_with(f"./copilot/{svc_name}/manifest.yml", "r")
    assert domain_name == "somedomain.tld"
    assert load_balancer_configuration["LoadBalancerArn"] == mocked_load_balancer_arn
    assert load_balancer_configuration["LoadBalancerName"] == "foo"
    assert load_balancer_configuration["VpcId"] == mocked_vpc_id
    assert load_balancer_configuration["AvailabilityZones"][0]["SubnetId"] == mocked_subnet_id


@pytest.mark.parametrize(
    "svc_name, content, exp_error",
    [
        ("testsvc1", """environments: {test: {http: {alias: }}}""", "No domains found"),
        ("testsvc2", """environments: {test: {http: }}""", "No domains found"),
        (
            "testsvc3",
            """environments: {not_test: {http: {alias: test.com}}}""",
            "Environment test not found",
        ),
    ],
)
@patch("dbt_platform_helper.utils.aws.get_load_balancer_configuration", return_value="test.com")
def test_get_load_balancer_domain_and_configuration_no_domain(
    get_load_balancer_configuration, fakefs, capsys, svc_name, content, exp_error
):
    fakefs.create_file(
        f"copilot/{svc_name}/manifest.yml",
        contents=content,
    )
    with pytest.raises(SystemExit):
        get_load_balancer_domain_and_configuration("test", "testapp", "test", svc_name)
    assert (
        capsys.readouterr().out
        == f"{exp_error}, please check the ./copilot/{svc_name}/manifest.yml file\n"
    )


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


# TODO - patching used here as a stop gap until this method is moved into its own provider, to be replaced with dependancy injection.
@patch("dbt_platform_helper.utils.aws.CacheProvider")
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
def test_get_supported_redis_versions_when_cache_refresh_required(
    mock_get_aws_session_or_abort, mock_cache_provider
):

    mock_cache_provider_instance = mock_cache_provider.return_value
    mock_cache_provider_instance.cache_refresh_required.return_value = True

    client = mock_aws_client(mock_get_aws_session_or_abort)
    client.describe_cache_engine_versions.return_value = {
        "CacheEngineVersions": [
            {
                "Engine": "redis",
                "EngineVersion": "4.0.10",
                "CacheParameterGroupFamily": "redis4.0",
                "CacheEngineDescription": "Redis",
                "CacheEngineVersionDescription": "redis version 4.0.10",
            },
            {
                "Engine": "redis",
                "EngineVersion": "5.0.6",
                "CacheParameterGroupFamily": "redis5.0",
                "CacheEngineDescription": "Redis",
                "CacheEngineVersionDescription": "redis version 5.0.6",
            },
        ]
    }

    supported_redis_versions_response = get_supported_redis_versions()
    assert supported_redis_versions_response == ["4.0.10", "5.0.6"]


# TODO - patching used here as a stop gap until this method is moved into its own provider, to be replaced with dependancy injection.
@patch("dbt_platform_helper.utils.aws.CacheProvider")
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
def test_get_supported_opensearch_versions_when_cache_refresh_required(
    mock_get_aws_session_or_abort, mock_cache_provider
):

    mock_cache_provider_instance = mock_cache_provider.return_value
    mock_cache_provider_instance.cache_refresh_required.return_value = True

    client = mock_aws_client(mock_get_aws_session_or_abort)
    client.list_versions.return_value = {
        "Versions": [
            "OpenSearch_2.15",
            "OpenSearch_2.13",
            "OpenSearch_2.11",
            "OpenSearch_2.9",
            "Elasticsearch_7.10",
            "Elasticsearch_7.9",
        ]
    }

    supported_opensearch_versions_response = get_supported_opensearch_versions()
    assert supported_opensearch_versions_response == ["2.15", "2.13", "2.11", "2.9"]


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


def mock_vpc_info_session():
    mock_session = Mock()
    mock_client = Mock()
    mock_session.client.return_value = mock_client
    vpc_data = {"Vpcs": [{"VpcId": "vpc-123456"}]}
    mock_client.describe_vpcs.return_value = vpc_data

    mock_resource = Mock()
    mock_session.resource.return_value = mock_resource
    mock_vpc = Mock()
    mock_resource.Vpc.return_value = mock_vpc

    mock_client.describe_route_tables.return_value = {
        "RouteTables": [
            {
                "Associations": [
                    {
                        "Main": False,
                        "RouteTableId": "rtb-09613a6769688def8",
                        "SubnetId": "subnet-private-1",
                    }
                ],
                "Routes": [
                    {
                        "DestinationCidrBlock": "10.151.0.0/16",
                        "GatewayId": "local",
                        "Origin": "CreateRouteTable",
                        "State": "active",
                    },
                    {
                        "DestinationCidrBlock": "0.0.0.0/0",
                        "NatGatewayId": "nat-05c4f248a6db4d724",
                        "Origin": "CreateRoute",
                        "State": "active",
                    },
                ],
                "VpcId": "vpc-010327b71b948b4bc",
                "OwnerId": "891377058512",
            },
            {
                "Associations": [
                    {
                        "Main": True,
                        "RouteTableId": "rtb-00cbf3c8d611a46b8",
                    }
                ],
                "Routes": [
                    {
                        "DestinationCidrBlock": "10.151.0.0/16",
                        "GatewayId": "local",
                        "Origin": "CreateRouteTable",
                        "State": "active",
                    }
                ],
                "VpcId": "vpc-010327b71b948b4bc",
                "OwnerId": "891377058512",
            },
            {
                "Associations": [
                    {
                        "Main": False,
                        "RouteTableId": "rtb-01caa2856120956c3",
                        "SubnetId": "subnet-public-1",
                    },
                    {
                        "Main": False,
                        "RouteTableId": "rtb-01caa2856120956c3",
                        "SubnetId": "subnet-public-2",
                    },
                ],
                "Routes": [
                    {
                        "DestinationCidrBlock": "10.151.0.0/16",
                        "GatewayId": "local",
                        "Origin": "CreateRouteTable",
                        "State": "active",
                    },
                    {
                        "DestinationCidrBlock": "0.0.0.0/0",
                        "GatewayId": "igw-0b2cbfdbb1cbd8a6b",
                        "Origin": "CreateRoute",
                        "State": "active",
                    },
                ],
                "OwnerId": "891377058512",
            },
            {
                "Associations": [
                    {
                        "Main": False,
                        "RouteTableId": "rtb-054dcff33741f4fe8",
                        "SubnetId": "subnet-private-2",
                    }
                ],
                "Routes": [
                    {
                        "DestinationCidrBlock": "10.151.0.0/16",
                        "GatewayId": "local",
                        "Origin": "CreateRouteTable",
                        "State": "active",
                    },
                    {
                        "DestinationCidrBlock": "0.0.0.0/0",
                        "NatGatewayId": "nat-08ead90aee75d601e",
                        "Origin": "CreateRoute",
                        "State": "active",
                    },
                ],
                "OwnerId": "891377058512",
            },
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


def test_get_vpc_info_by_name_success():
    mock_session, mock_client, _ = mock_vpc_info_session()

    result = get_vpc_info_by_name(mock_session, "my_app", "my_env", "my_vpc")

    expected_vpc = Vpc(
        subnets=["subnet-private-1", "subnet-private-2"], security_groups=["sg-abc123"]
    )

    mock_client.describe_vpcs.assert_called_once_with(
        Filters=[{"Name": "tag:Name", "Values": ["my_vpc"]}]
    )

    assert result.subnets == expected_vpc.subnets
    assert result.security_groups == expected_vpc.security_groups


def test_get_vpc_info_by_name_failure_no_matching_vpc():
    mock_session, mock_client, _ = mock_vpc_info_session()

    vpc_data = {"Vpcs": []}
    mock_client.describe_vpcs.return_value = vpc_data

    with pytest.raises(AWSException) as ex:
        get_vpc_info_by_name(mock_session, "my_app", "my_env", "my_vpc")

    assert "VPC not found for name 'my_vpc'" in str(ex)


def test_get_vpc_info_by_name_failure_no_vpc_id_in_response():
    mock_session, mock_client, _ = mock_vpc_info_session()

    vpc_data = {"Vpcs": [{"Id": "abc123"}]}
    mock_client.describe_vpcs.return_value = vpc_data

    with pytest.raises(AWSException) as ex:
        get_vpc_info_by_name(mock_session, "my_app", "my_env", "my_vpc")

    assert "VPC id not present in vpc 'my_vpc'" in str(ex)


def test_get_vpc_info_by_name_failure_no_private_subnets_in_vpc():
    mock_session, mock_client, mock_vpc = mock_vpc_info_session()

    mock_client.describe_route_tables.return_value = {
        "RouteTables": [
            {
                "Associations": [
                    {
                        "Main": True,
                        "RouteTableId": "rtb-00cbf3c8d611a46b8",
                    }
                ],
                "Routes": [
                    {
                        "DestinationCidrBlock": "10.151.0.0/16",
                        "GatewayId": "local",
                        "Origin": "CreateRouteTable",
                        "State": "active",
                    }
                ],
                "VpcId": "vpc-010327b71b948b4bc",
                "OwnerId": "891377058512",
            }
        ]
    }

    with pytest.raises(AWSException) as ex:
        get_vpc_info_by_name(mock_session, "my_app", "my_env", "my_vpc")

    assert "No private subnets found in vpc 'my_vpc'" in str(ex)


def test_get_vpc_info_by_name_failure_no_matching_security_groups():
    mock_session, mock_client, mock_vpc = mock_vpc_info_session()

    mock_vpc.security_groups.all.return_value = [
        ObjectWithId("sg-abc345", tags=[]),
        ObjectWithId("sg-abc567", tags=[{"Key": "Name", "Value": "copilot-other_app-my_env-env"}]),
        ObjectWithId("sg-abc456"),
        ObjectWithId("sg-abc678", tags=[{"Key": "Name", "Value": "copilot-my_app-other_env-env"}]),
    ]

    with pytest.raises(AWSException) as ex:
        get_vpc_info_by_name(mock_session, "my_app", "my_env", "my_vpc")

    assert "No matching security groups found in vpc 'my_vpc'" in str(ex)


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
