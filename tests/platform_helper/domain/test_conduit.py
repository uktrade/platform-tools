from unittest.mock import Mock

import boto3
import pytest
from botocore.stub import Stubber

from dbt_platform_helper.domain.conduit import AddonNotFoundConduitError
from dbt_platform_helper.domain.conduit import Conduit
from dbt_platform_helper.domain.conduit import CreateTaskTimeoutConduitError
from dbt_platform_helper.domain.conduit import InvalidAddonTypeConduitError
from dbt_platform_helper.domain.conduit import NoClusterConduitError
from dbt_platform_helper.domain.conduit import ParameterNotFoundConduitError
from dbt_platform_helper.domain.conduit import SecretNotFoundConduitError
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import Environment


# @pytest.fixture(scope="function")
# def ecs_session(aws_credentials):
#     with mock_aws():
#         session = boto3.session.Session(profile_name="foo", region_name="eu-west-2")
#         yield session
#
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
    session = boto3.session.Session(profile_name="lite", region_name="eu-west-2")
    ecs_client = session.client("ecs")
    ecs_stubber = Stubber(ecs_client)
    ecs_list_tasks_response = {"taskArns": ["test_arn"], "nextToken": ""}
    ecs_stubber.add_response(
        "list_tasks",
        ecs_list_tasks_response,
        {
            "cluster": "cluster_arn",
            "desiredStatus": "RUNNING",
            "family": "copilot-task_name",
        },
    )

    ecs_stubber.activate()

    with ecs_stubber:
        env = "dev"

        # ecs_list_tasks_response = {"taskArns": ["test_arn"], "nextToken": ""}
        # stubber = Stubber(ecs_session.client("ecs"))
        # stubber.create_cluster(clusterName="something")
        # stubber.activate()

        # stubber.add_response(
        #     "list_tasks",
        #     ecs_list_tasks_response,
        #     {
        #         "cluster": "cluster_arn",
        #         "desiredStatus": "RUNNING",
        #         "family": "copilot-task_name",
        #     }
        # )
        #
        # mock_client.describe_tasks.return_value = {
        #     "tasks": [
        #         {
        #             "containers": [
        #                 {"managedAgents": [{"name": "ExecuteCommandAgent", "lastStatus": "RUNNING"}]}
        #             ]
        #         }
        #     ]
        # }
        sessions = {"000000000": session}
        mock_application = Application(app_name)
        mock_application.environments = {env: Environment(env, "000000000", sessions)}
        mock_subprocess = Mock()

        conduit = Conduit(mock_application, mock_subprocess)
        ecs_stubber = Stubber(conduit.ecs_client)
        ecs_stubber.activate()

        ecs_list_tasks_response = {"taskArns": ["test_arn"], "nextToken": ""}
        ecs_stubber.add_response(
            "list_tasks",
            ecs_list_tasks_response,
            {
                "cluster": "cluster_arn",
                "desiredStatus": "RUNNING",
                "family": "copilot-task_name",
            },
        )

        conduit.start(env, addon_name, addon_type, access)

    # stubber.add_response(
    #     "list_tasks",
    #     ecs_list_tasks_response,
    #     {
    #         "cluster": "cluster_arn",
    #         "desiredStatus": "RUNNING",
    #         "family": "copilot-task_name",
    #     }
    # )
    #
    # # conduit = Conduit(mock_application, mock_subprocess)
    #
    # conduit.start(env, addon_name, addon_type, access)
    #
    # mock_session.client.assert_called_with("ecs")
    # mock_client.list_tasks.assert_called_once_with(
    #     cluster=cluster_arn,
    #     desiredStatus="RUNNING",
    #     family=f"copilot-{task_name}",
    # )
    # # mock_client.describe_tasks()
    # mock_subprocess.call.assert_called_once_with(
    #     "copilot task exec "
    #     f"--app {app_name} --env {env} "
    #     f"--name {task_name} "
    #     f"--command bash",
    #     shell=True,
    # )


# TODO
# Test retry of client_is_running check


def test_conduit_domain_when_no_cluster_exists():
    # mock application
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

    conduit = Conduit(mock_application)

    with pytest.raises(NoClusterConduitError) as exc:
        conduit.start(env, addon_name, addon_type, access)


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

    conduit = Conduit(mock_application, mock_subprocess)

    with pytest.raises(SecretNotFoundConduitError) as exc:
        conduit.start(env, addon_name, addon_type, access)


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

    conduit = Conduit(mock_application, mock_subprocess)

    with pytest.raises(CreateTaskTimeoutConduitError) as exc:
        conduit.start(env, addon_name, addon_type, access)


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

    conduit = Conduit(mock_application)

    with pytest.raises(InvalidAddonTypeConduitError) as exc:
        conduit.start(env, addon_name, addon_type, access)
        mock_session.client.assert_called_with("ssm")
        mock_session.client.assert_called_with("secretsmanager")
        mock_session.client.assert_called_with("cloudformation")
        mock_session.client.assert_called_with("iam")

        # mock_client.list_stack_resources
        # mock_client.describe_secret


# TODO conduit requires addon type
def test_conduit_domain_when_addon_does_not_exist():
    app_name = "failed_app"
    addon_name = "addon_doesnt_exist"
    addon_type = "postgres"
    env = "dev"
    access = "admin"

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.list_tasks.return_value = {"taskArns": [], "nextToken": ""}
    sessions = {"000000000": mock_session}
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}

    conduit = Conduit(mock_application)

    with pytest.raises(AddonNotFoundConduitError) as exc:
        conduit.start(env, addon_name, addon_type, access)


# TODO conduit requires addon type
def test_conduit_domain_when_no_addon_config_parameter_exists():
    app_name = "failed_app"
    addon_name = "parameter_doesnt_exist"
    addon_type = "postgres"
    env = "dev"
    access = "admin"

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.list_tasks.return_value = {"taskArns": [], "nextToken": ""}
    sessions = {"000000000": mock_session}
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}

    conduit = Conduit(mock_application)

    with pytest.raises(ParameterNotFoundConduitError) as exc:
        conduit.start(env, addon_name, addon_type, access)


"""

    mock_client_attrs = {'get_parameter.side_effect': set_get_parameter_return_value}

    mock_client.configure_mock(**mock_client_attrs)

    def set_get_parameter_return_value(Name,WithDecryption):
        print("param name for side effect: %s",Name)
        if Name == f"/copilot/{app_name}/{env}/secrets/{addon_name}_RDS_MASTER_ARN":
            return {
            "Parameter": {
                "Value": "arn::some-arn",
                "Name": f"/copilot/{app_name}/{env}/secrets/{addon_name}_RDS_MASTER_ARN",
            }
        }
        elif Name == f"/copilot/{app_name}/{env}/secrets/{normalise_secret_name(addon_name)}_READ_ONLY_USER":
            return {
                "Parameter": {
                    "Value": {
                        "username": "read_only",
                        "password": "fake_pass",
                        "engine": "postgres", 
                        "port": 5432, 
                        "dbname": "main", 
                        "host": "demodjango-anthoni-demodjango-postgres..eu-west-2.rds.amazonaws.com", 
                        "dbInstanceIdentifier": "db-XXXXXXXXXXXXXXX"
                        },
                    "Name": f"/copilot/{app_name}/{env}/secrets/{normalise_secret_name(addon_name)}_READ_ONLY_USER",
                    },
            } 

"""
