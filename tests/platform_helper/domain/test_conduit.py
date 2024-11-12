from unittest.mock import Mock

import boto3
import pytest

from dbt_platform_helper.domain.conduit import Conduit
from dbt_platform_helper.providers.aws import SecretNotFoundError
from dbt_platform_helper.providers.copilot import AddonNotFoundError
from dbt_platform_helper.providers.copilot import CreateTaskTimeoutError
from dbt_platform_helper.providers.copilot import InvalidAddonTypeError
from dbt_platform_helper.providers.copilot import NoClusterError
from dbt_platform_helper.providers.copilot import ParameterNotFoundError
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import Environment


@pytest.mark.parametrize(
    "app_name, addon_type, addon_name, access",
    [
        ("app_1", "postgres", "custom-name-postgres", "read"),
        ("app_2", "postgres", "custom-name-rds-postgres", "read"),
        ("app_1", "redis", "custom-name-redis", "read"),
        ("app_1", "opensearch", "custom-name-opensearch", "read"),
    ],
)
def test_conduit(app_name, addon_type, addon_name, access, aws_credentials):
    session = boto3.session.Session(profile_name="foo", region_name="eu-west-2")
    env = "dev"
    sessions = {"000000000": session}
    dummy_application = Application(app_name)
    dummy_application.environments = {env: Environment(env, "000000000", sessions)}
    mock_subprocess = Mock()
    addon_client_is_running_fn = Mock(return_value=True)
    connect_to_addon_client_task_fn = Mock()
    create_addon_client_task_fn = Mock()
    create_postgres_admin_task_fn = Mock()
    get_addon_type_fn = Mock(return_value=addon_type)
    get_cluster_arn_fn = Mock(
        return_value="arn:aws:ecs:eu-west-2:123456789012:cluster/MyECSCluster1"
    )
    get_or_create_task_name_fn = Mock(return_value="task_name")
    add_stack_delete_policy_to_task_role_fn = Mock()
    update_conduit_stack_resources_fn = Mock()

    conduit = Conduit(
        application=dummy_application,
        subprocess=mock_subprocess,
        addon_client_is_running_fn=addon_client_is_running_fn,
        connect_to_addon_client_task_fn=connect_to_addon_client_task_fn,
        create_addon_client_task_fn=create_addon_client_task_fn,
        create_postgres_admin_task_fn=create_postgres_admin_task_fn,
        get_addon_type_fn=get_addon_type_fn,
        get_cluster_arn_fn=get_cluster_arn_fn,
        get_or_create_task_name_fn=get_or_create_task_name_fn,
        add_stack_delete_policy_to_task_role_fn=add_stack_delete_policy_to_task_role_fn,
        update_conduit_stack_resources_fn=update_conduit_stack_resources_fn,
    )

    conduit.start(env, addon_name, access)


# TODO
# Test retry of client_is_running check


def test_conduit_domain_when_no_cluster_exists():
    app_name = "failed_app"
    addon_name = ""
    addon_type = "postgres"
    env = "dev"
    access = "admin"

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    sessions = {"000000000": mock_session}
    get_addon_type_fn = Mock(return_value=addon_type)
    get_cluster_arn_fn = Mock(side_effect=NoClusterError())
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}
    mock_client.describe_tasks.return_value = {
        "tasks": [
            {
                "containers": [
                    {
                        "managedAgents": {
                            "name": "ExecuteCommandAgent",
                            "lastStatus": "RUNNING",
                        }
                    }
                ]
            },
            {
                "containers": [
                    {
                        "managedAgents": {
                            "name": "ExecuteCommandAgent",
                            "lastStatus": "RUNNING",
                        }
                    }
                ]
            },
        ]
    }

    conduit = Conduit(
        mock_application,
        get_addon_type_fn=get_addon_type_fn,
        get_cluster_arn_fn=get_cluster_arn_fn,
    )

    with pytest.raises(NoClusterError) as exc:
        conduit.start(env, addon_name, access)


# TODO when the connection details to the addon does not exist
def test_conduit_domain_when_no_connection_secret_exists():
    app_name = "failed_app"
    addon_name = ""
    addon_type = "postgres"
    env = "dev"
    access = "admin"

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.list_tasks.return_value = {"taskArns": ["test_arn"], "nextToken": ""}
    sessions = {"000000000": mock_session}
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}
    mock_subprocess = Mock()
    get_addon_type_fn = Mock(return_value=addon_type)
    get_cluster_arn_fn = Mock(
        return_value="arn:aws:ecs:eu-west-2:123456789012:cluster/MyECSCluster1"
    )
    get_or_create_task_name_fn = Mock(return_value="task_name")
    addon_client_is_running_fn = Mock(return_value=False)
    create_addon_client_task_fn = Mock(side_effect=SecretNotFoundError())

    conduit = Conduit(
        mock_application,
        mock_subprocess,
        addon_client_is_running_fn=addon_client_is_running_fn,
        create_addon_client_task_fn=create_addon_client_task_fn,
        get_addon_type_fn=get_addon_type_fn,
        get_cluster_arn_fn=get_cluster_arn_fn,
        get_or_create_task_name_fn=get_or_create_task_name_fn,
    )

    with pytest.raises(SecretNotFoundError) as exc:
        conduit.start(env, addon_name, access)


def test_conduit_domain_when_client_task_fails_to_start():
    app_name = "failed_app"
    addon_name = ""
    addon_type = "postgres"
    env = "dev"
    access = "admin"
    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.get_parameter.return_value = {
        "Parameter": {
            "Value": "arn::some-arn",
            "Name": "/copilot/{app_name}/{env}/secrets/{addon_name}_RDS_MASTER_ARN",
        }
    }
    mock_client.list_tasks.return_value = {"taskArns": [], "nextToken": ""}
    sessions = {"000000000": mock_session}
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}
    mock_subprocess = Mock()
    get_addon_type_fn = Mock(return_value=addon_type)
    get_cluster_arn_fn = Mock(
        return_value="arn:aws:ecs:eu-west-2:123456789012:cluster/MyECSCluster1"
    )
    get_or_create_task_name_fn = Mock(return_value="task_name")
    # TODO add test where return value is False
    addon_client_is_running_fn = Mock(return_value=True)

    connect_to_addon_client_task_fn = Mock(side_effect=CreateTaskTimeoutError())

    conduit = Conduit(
        mock_application,
        mock_subprocess,
        addon_client_is_running_fn=addon_client_is_running_fn,
        connect_to_addon_client_task_fn=connect_to_addon_client_task_fn,
        get_addon_type_fn=get_addon_type_fn,
        get_cluster_arn_fn=get_cluster_arn_fn,
        get_or_create_task_name_fn=get_or_create_task_name_fn,
    )

    with pytest.raises(CreateTaskTimeoutError) as exc:
        conduit.start(env, addon_name, access)


def normalise_secret_name(addon_name: str) -> str:
    return addon_name.replace("-", "_").upper()


# TODO add test for failing to retrieve session.client("iam").get_role(RoleName=role_name)


# TODO conduit requires addon type
def test_conduit_domain_when_addon_type_is_invalid():

    app_name = "failed_app"
    addon_name = "invalid_addon"
    addon_type = "postgres"
    env = "dev"
    access = "read"

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.list_tasks.return_value = {"taskArns": [], "nextToken": ""}
    mock_client.get_parameter.return_value = {
        "Parameter": {
            "Value": "secret value",
            "ARN": "arn::some-arn",
            "Name": "/copilot/{app_name}/{env}/secrets/{addon_name}_RDS_MASTER_ARN",
        }
    }

    mock_client.describe_secret.return_value = {
        "ARN": "arn:aws:secretsmanager:eu-west-2:123456789012:secret:MyTestSecret-Ca8JGt",
        "Name": "MyTestSecret",
        "Description": "My test secret",
    }

    # mock copied from example output of aws command
    mock_client.list_stack_resources.return_value = {
        "StackResourceSummaries": [
            {
                "LogicalResourceId": "bucket",
                "PhysicalResourceId": "my-stack-bucket-1vc62xmplgguf",
                "ResourceType": "AWS::S3::Bucket",
                "LastUpdatedTimestamp": "2019-10-02T04:34:11.345Z",
                "ResourceStatus": "CREATE_COMPLETE",
                "DriftInformation": {"StackResourceDriftStatus": "IN_SYNC"},
            },
            {
                "LogicalResourceId": "function",
                "PhysicalResourceId": "my-function-SEZV4XMPL4S5",
                "ResourceType": "AWS::Lambda::Function",
                "LastUpdatedTimestamp": "2019-10-02T05:34:27.989Z",
                "ResourceStatus": "UPDATE_COMPLETE",
                "DriftInformation": {"StackResourceDriftStatus": "IN_SYNC"},
            },
            {
                "LogicalResourceId": "functionRole",
                "PhysicalResourceId": "my-functionRole-HIZXMPLEOM9E",
                "ResourceType": "AWS::IAM::Role",
                "LastUpdatedTimestamp": "2019-10-02T04:34:06.350Z",
                "ResourceStatus": "CREATE_COMPLETE",
                "DriftInformation": {"StackResourceDriftStatus": "IN_SYNC"},
            },
        ]
    }

    mock_client.get_template.return_value = {
        "TemplateBody": {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Outputs": {
                "BucketName": {
                    "Description": "Name of S3 bucket to hold website content",
                    "Value": {"Ref": "S3Bucket"},
                }
            },
            "Description": "AWS CloudFormation Sample Template S3_Bucket: Sample template showing how to create a publicly accessible S3 bucket. **WARNING** This template creates an S3 bucket. You will be billed for the AWS resources used if you create a stack from this template.",
            "Resources": {
                "S3Bucket": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {"AccessControl": "PublicRead"},
                }
            },
        }
    }

    mock_client.get_role.return_value = {
        "Role": {
            "Description": "Test Role",
            "AssumeRolePolicyDocument": "<URL-encoded-JSON>",
            "MaxSessionDuration": 3600,
            "RoleId": "AROA1234567890EXAMPLE",
            "CreateDate": "2019-11-13T16:45:56Z",
            "RoleName": "Test-Role",
            "Path": "/",
            "RoleLastUsed": {"Region": "eu-west-2", "LastUsedDate": "2019-11-13T17:14:00Z"},
            "Arn": "arn:aws:iam::123456789012:role/Test-Role",
        }
    }

    # mocks line 159: ssm_client.get_parameter(Name="/copilot/tools/central_log_groups")
    # but already mocked .... TODO fix
    # mock_client.get_parameter.return_value =

    sessions = {"000000000": mock_session}
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}

    get_addon_type_fn = Mock(side_effect=InvalidAddonTypeError(addon_type=addon_type))

    conduit = Conduit(
        mock_application,
        get_addon_type_fn=get_addon_type_fn,
    )

    with pytest.raises(InvalidAddonTypeError) as exc:
        conduit.start(env, addon_name, access)


# TODO conduit requires addon type
def test_conduit_domain_when_addon_does_not_exist():
    app_name = "failed_app"
    addon_name = "addon_doesnt_exist"
    env = "dev"
    access = "admin"

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.list_tasks.return_value = {"taskArns": [], "nextToken": ""}
    sessions = {"000000000": mock_session}
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}

    get_addon_type_fn = Mock(side_effect=AddonNotFoundError())

    conduit = Conduit(
        mock_application,
        get_addon_type_fn=get_addon_type_fn,
    )

    with pytest.raises(AddonNotFoundError) as exc:
        conduit.start(env, addon_name, access)


# TODO conduit requires addon type
def test_conduit_domain_when_no_addon_config_parameter_exists():
    app_name = "failed_app"
    addon_name = "parameter_doesnt_exist"
    env = "dev"
    access = "admin"

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.list_tasks.return_value = {"taskArns": [], "nextToken": ""}
    sessions = {"000000000": mock_session}
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}

    get_addon_type_fn = Mock(side_effect=ParameterNotFoundError())

    conduit = Conduit(
        mock_application,
        get_addon_type_fn=get_addon_type_fn,
    )

    with pytest.raises(ParameterNotFoundError) as exc:
        conduit.start(env, addon_name, access)
