import re
from datetime import date
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import boto3
import pytest
import yaml
from botocore.exceptions import ClientError
from moto import mock_aws

from dbt_platform_helper.providers.aws import CreateTaskTimeoutException
from dbt_platform_helper.providers.copilot import CopilotProvider
from dbt_platform_helper.providers.copilot import connect_to_addon_client_task
from dbt_platform_helper.providers.copilot import create_addon_client_task
from dbt_platform_helper.providers.copilot import create_postgres_admin_task
from dbt_platform_helper.providers.secrets import SecretNotFoundException
from tests.platform_helper.conftest import NoSuchEntityException
from tests.platform_helper.conftest import expected_connection_secret_name
from tests.platform_helper.conftest import mock_task_name

env = "development"


def environments():
    return {
        "dev": {"accounts": {"deploy": {"name": "dev-acc", "id": "123456789010"}}},
        "staging": {"accounts": {"deploy": {"name": "dev-acc", "id": "123456789010"}}},
        "hotfix": {"accounts": {"deploy": {"name": "prod-acc", "id": "987654321010"}}},
        "prod": {"accounts": {"deploy": {"name": "prod-acc", "id": "987654321010"}}},
    }


def s3_xenv_extensions():
    return {
        "test-s3-bucket-x-account": {
            "type": "s3",
            "services": "test-svc",
            "environments": {
                "hotfix": {
                    "bucket_name": "x-acc-bucket",
                    "cross_environment_service_access": {
                        "test_access": {
                            "application": "app2",
                            "environment": "staging",
                            "account": "123456789010",
                            "service": "test_svc",
                            "read": True,
                            "write": True,
                            "cyber_sign_off_by": "user@example.com",
                        }
                    },
                }
            },
        }
    }


def s3_xenv_multiple_extensions():
    return {
        "test-s3-1": {
            "type": "s3",
            "services": "test-svc",
            "environments": {
                "hotfix": {
                    "bucket_name": "x-acc-bucket-1",
                    "cross_environment_service_access": {
                        "test_access_1": {
                            "application": "app1",
                            "environment": "staging",
                            "account": "123456789010",
                            "service": "other_svc_1",
                            "read": True,
                            "write": True,
                            "cyber_sign_off_by": "user1@example.com",
                        },
                        "test_access_2": {
                            "application": "app2",
                            "environment": "dev",
                            "account": "123456789010",
                            "service": "other_svc_2",
                            "read": True,
                            "write": False,
                            "cyber_sign_off_by": "user2@example.com",
                        },
                    },
                },
            },
        },
        "test-s3-2": {
            "type": "s3",
            "services": "test-svc",
            "environments": {
                "dev": {
                    "bucket_name": "x-acc-bucket-2",
                    "cross_environment_service_access": {
                        "test_access_3": {
                            "application": "app2",
                            "environment": "hotfix",
                            "account": "987654321010",
                            "service": "other_svc_2",
                            "read": False,
                            "write": True,
                            "cyber_sign_off_by": "user@example.com",
                        }
                    },
                },
                "prod": {
                    "bucket_name": "x-acc-bucket-3",
                    "cross_environment_service_access": {
                        "test_access_4": {
                            "application": "app2",
                            "environment": "staging",
                            "account": "123456789010",
                            "service": "other_svc_3",
                            "read": True,
                            "write": True,
                            "cyber_sign_off_by": "user@example.com",
                        }
                    },
                },
                "hotfix": {
                    "bucket_name": "x-acc-bucket-4",
                    "cross_environment_service_access": {
                        "test_access_5": {
                            "application": "app2",
                            "environment": "staging",
                            "account": "123456789010",
                            "service": "other_svc_4",
                            "read": False,
                            "write": False,
                            "cyber_sign_off_by": "user@example.com",
                        }
                    },
                },
            },
        },
    }


def test_generate_cross_account_s3_policies():
    """
    Tests the happy path test for the simple case.

    Also tests passed in templates
    """
    mock_mkfile = Mock()
    provider = CopilotProvider(mkfile_fn=mock_mkfile)
    provider.generate_cross_account_s3_policies(environments(), s3_xenv_extensions())

    assert mock_mkfile.call_count == 1

    calls = mock_mkfile.call_args_list

    act_output_dir = calls[0][0][0]
    act_output_path = calls[0][0][1]
    act_content = calls[0][0][2]
    act_overwrite_file = calls[0][0][3]

    assert_headers_present(act_content)

    assert act_output_dir == Path(".").absolute()
    assert act_output_path == "copilot/test_svc/addons/s3-cross-account-policy.yml"
    assert act_overwrite_file

    act = yaml.safe_load(act_content)

    assert act["Parameters"]["App"]["Type"] == "String"
    assert act["Parameters"]["Env"]["Type"] == "String"
    assert act["Parameters"]["Name"]["Type"] == "String"

    assert (
        act["Outputs"]["testSvcXAccBucketTestAccessXEnvAccessPolicy"]["Description"]
        == "The IAM::ManagedPolicy to attach to the task role"
    )
    assert (
        act["Outputs"]["testSvcXAccBucketTestAccessXEnvAccessPolicy"]["Value"]["Ref"]
        == "testSvcXAccBucketTestAccessXEnvAccessPolicy"
    )

    policy = act["Resources"]["testSvcXAccBucketTestAccessXEnvAccessPolicy"]
    assert (
        policy["Metadata"]["aws:copilot:description"]
        == "An IAM ManagedPolicy for your service to access the bucket"
    )
    assert policy["Type"] == "AWS::IAM::ManagedPolicy"

    policy_doc = policy["Properties"]["PolicyDocument"]
    assert policy_doc["Version"] == date(2012, 10, 17)
    statements = policy_doc["Statement"]
    kms_statement = statements[0]
    assert kms_statement["Sid"] == "KMSDecryptAndGenerate"
    assert kms_statement["Effect"] == "Allow"
    assert kms_statement["Action"] == ["kms:Decrypt", "kms:GenerateDataKey"]
    assert kms_statement["Resource"] == "arn:aws:kms:eu-west-2:987654321010:key/*"
    assert kms_statement["Condition"] == {
        "StringEquals": {"aws:PrincipalTag/copilot-environment": ["staging"]}
    }

    s3_obj_statement = statements[1]
    assert s3_obj_statement["Sid"] == "S3ObjectActions"
    assert s3_obj_statement["Effect"] == "Allow"
    assert s3_obj_statement["Action"] == ["s3:Get*", "s3:Put*"]
    assert s3_obj_statement["Resource"] == "arn:aws:s3:::x-acc-bucket/*"
    assert s3_obj_statement["Condition"] == {
        "StringEquals": {"aws:PrincipalTag/copilot-environment": ["staging"]}
    }

    s3_list_statement = statements[2]
    assert s3_list_statement["Sid"] == "S3ListAction"
    assert s3_list_statement["Effect"] == "Allow"
    assert s3_list_statement["Action"] == ["s3:ListBucket"]
    assert s3_list_statement["Resource"] == "arn:aws:s3:::x-acc-bucket"
    assert s3_list_statement["Condition"] == {
        "StringEquals": {"aws:PrincipalTag/copilot-environment": ["staging"]}
    }


def assert_headers_present(act_content):
    content_lines = [line.strip() for line in act_content.split("\n", 3)]
    assert content_lines[0] == "# WARNING: This is an autogenerated file, not for manual editing."
    assert re.match(
        r"# Generated by platform-helper \d+\.\d+\.\d+ / \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
        content_lines[1],
    )


def test_generate_cross_account_s3_policies_no_addons():
    mock_mkfile = Mock()
    provider = CopilotProvider(mkfile_fn=mock_mkfile)
    provider.generate_cross_account_s3_policies(environments(), {})

    assert mock_mkfile.call_count == 0


def test_generate_cross_account_s3_policies_multiple_addons():
    """More comprehensive tests that check multiple corner cases."""
    mock_mkfile = Mock()
    provider = CopilotProvider(mkfile_fn=mock_mkfile)
    provider.generate_cross_account_s3_policies(environments(), s3_xenv_multiple_extensions())

    assert mock_mkfile.call_count == 3

    calls = mock_mkfile.call_args_list

    # Case 1: hotfix -> staging. other_svc_1
    act_output_dir = calls[0][0][0]
    act_output_path = calls[0][0][1]
    act_content = calls[0][0][2]
    act_overwrite_file = calls[0][0][3]
    act = yaml.safe_load(act_content)

    assert_headers_present(act_content)
    assert act_output_dir == Path(".").absolute()
    assert act_output_path == "copilot/other_svc_1/addons/s3-cross-account-policy.yml"
    assert act_overwrite_file

    assert act["Parameters"]["App"]["Type"] == "String"
    assert act["Parameters"]["Env"]["Type"] == "String"
    assert act["Parameters"]["Name"]["Type"] == "String"

    assert len(act["Outputs"]) == 1
    assert (
        act["Outputs"]["otherSvc1XAccBucket1TestAccess1XEnvAccessPolicy"]["Value"]["Ref"]
        == "otherSvc1XAccBucket1TestAccess1XEnvAccessPolicy"
    )
    assert len(act["Resources"]) == 1

    principal_tag = "aws:PrincipalTag/copilot-environment"

    policy_doc1 = act["Resources"]["otherSvc1XAccBucket1TestAccess1XEnvAccessPolicy"]["Properties"][
        "PolicyDocument"
    ]
    kms_statement1 = policy_doc1["Statement"][0]
    assert kms_statement1["Condition"]["StringEquals"][principal_tag] == ["staging"]
    assert kms_statement1["Resource"] == "arn:aws:kms:eu-west-2:987654321010:key/*"
    obj_act_statement1 = policy_doc1["Statement"][1]
    assert obj_act_statement1["Action"] == ["s3:Get*", "s3:Put*"]

    # Case 2: hotfix -> dev and dev -> hotfix. other_svc_2
    act_output_dir = calls[1][0][0]
    act_output_path = calls[1][0][1]
    act_content = calls[1][0][2]
    act_overwrite_file = calls[1][0][3]
    act = yaml.safe_load(act_content)

    assert_headers_present(act_content)
    assert act_output_dir == Path(".").absolute()
    assert act_output_path == "copilot/other_svc_2/addons/s3-cross-account-policy.yml"
    assert act_overwrite_file

    assert act["Parameters"]["App"]["Type"] == "String"
    assert act["Parameters"]["Env"]["Type"] == "String"
    assert act["Parameters"]["Name"]["Type"] == "String"

    assert len(act["Outputs"]) == 2
    assert (
        act["Outputs"]["otherSvc2XAccBucket1TestAccess2XEnvAccessPolicy"]["Value"]["Ref"]
        == "otherSvc2XAccBucket1TestAccess2XEnvAccessPolicy"
    )
    assert (
        act["Outputs"]["otherSvc2XAccBucket2TestAccess3XEnvAccessPolicy"]["Value"]["Ref"]
        == "otherSvc2XAccBucket2TestAccess3XEnvAccessPolicy"
    )

    policy_doc2 = act["Resources"]["otherSvc2XAccBucket1TestAccess2XEnvAccessPolicy"]["Properties"][
        "PolicyDocument"
    ]
    kms_statement2 = policy_doc2["Statement"][0]
    assert kms_statement2["Condition"]["StringEquals"][principal_tag] == ["dev"]
    assert kms_statement2["Resource"] == "arn:aws:kms:eu-west-2:987654321010:key/*"
    obj_act_statement2 = policy_doc2["Statement"][1]
    assert obj_act_statement2["Action"] == ["s3:Get*"]

    policy_doc3 = act["Resources"]["otherSvc2XAccBucket2TestAccess3XEnvAccessPolicy"]["Properties"][
        "PolicyDocument"
    ]
    kms_statement3 = policy_doc3["Statement"][0]
    assert kms_statement3["Condition"]["StringEquals"][principal_tag] == ["hotfix"]
    assert kms_statement3["Resource"] == "arn:aws:kms:eu-west-2:123456789010:key/*"
    obj_act_statement3 = policy_doc3["Statement"][1]
    assert obj_act_statement3["Action"] == ["s3:Put*"]

    # Case 3: prod -> staging. other_svc_3
    act_output_dir = calls[2][0][0]
    act_output_path = calls[2][0][1]
    act_content = calls[2][0][2]
    act_overwrite_file = calls[2][0][3]
    act = yaml.safe_load(act_content)

    assert_headers_present(act_content)
    assert act_output_dir == Path(".").absolute()
    assert act_output_path == "copilot/other_svc_3/addons/s3-cross-account-policy.yml"
    assert act_overwrite_file

    assert act["Parameters"]["App"]["Type"] == "String"
    assert act["Parameters"]["Env"]["Type"] == "String"
    assert act["Parameters"]["Name"]["Type"] == "String"

    assert len(act["Outputs"]) == 1

    assert (
        act["Outputs"]["otherSvc3XAccBucket3TestAccess4XEnvAccessPolicy"]["Value"]["Ref"]
        == "otherSvc3XAccBucket3TestAccess4XEnvAccessPolicy"
    )
    policy_doc4 = act["Resources"]["otherSvc3XAccBucket3TestAccess4XEnvAccessPolicy"]["Properties"][
        "PolicyDocument"
    ]
    kms_statement4 = policy_doc4["Statement"][0]
    assert kms_statement4["Condition"]["StringEquals"][principal_tag] == ["staging"]
    assert kms_statement4["Resource"] == "arn:aws:kms:eu-west-2:987654321010:key/*"
    obj_act_statement4 = policy_doc4["Statement"][1]
    assert obj_act_statement4["Action"] == ["s3:Get*", "s3:Put*"]


@mock_aws
@patch(  # Nested function within provider function
    "dbt_platform_helper.providers.secrets.Secrets.get_postgres_connection_data_updated_with_master_secret",
    return_value="connection string",
)
def test_create_postgres_admin_task(mock_update_parameter, mock_application):

    addon_name = "dummy-postgres"
    master_secret_name = (
        f"/copilot/{mock_application.name}/{env}/secrets/DUMMY_POSTGRES_RDS_MASTER_ARN"
    )
    ssm_client = mock_application.environments[env].session.client("ssm")

    boto3.client("ssm").put_parameter(
        Name=master_secret_name, Value="master-secret-arn", Type="String"
    )
    mock_subprocess = Mock()

    create_postgres_admin_task(
        ssm_client,
        mock_subprocess,
        mock_application,
        addon_name,
        "postgres",
        env,
        "POSTGRES_SECRET_NAME",
        "test-task",
    )

    mock_update_parameter.assert_called_once_with(
        "POSTGRES_SECRET_NAME_READ_ONLY_USER",
        "master-secret-arn",
    )

    mock_subprocess.call.assert_called_once_with(
        f"copilot task run --app {mock_application.name} --env {env} "
        f"--task-group-name test-task "
        "--image public.ecr.aws/uktrade/tunnel:postgres "
        "--env-vars CONNECTION_SECRET='\"connection string\"' "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


@pytest.mark.parametrize(
    "access",
    [
        "read",
        "write",
        "admin",
    ],
)
@pytest.mark.parametrize(
    "addon_type, addon_name",
    [
        ("redis", "custom-name-redis"),
        ("opensearch", "custom-name-opensearch"),
    ],
)
@patch(
    "dbt_platform_helper.providers.secrets.Secrets.get_connection_secret_arn",
    return_value="test-arn",
)
def test_create_redis_or_opensearch_addon_client_task(
    get_connection_secret_arn,
    access,
    addon_type,
    addon_name,
):
    """Test that, given app, env and permissions, create_addon_client_task calls
    get_connection_secret_arn with the default secret name and subsequently
    subprocess.call with the correct secret ARN and execution role."""

    mock_application = Mock()
    mock_application.name = "test-application"
    mock_application.environments = {"development": Mock()}
    task_name = mock_task_name(addon_name)
    mock_subprocess = Mock()

    iam_client = mock_application.environments[env].session.client("iam")
    ssm_client = mock_application.environments[env].session.client("ssm")

    create_addon_client_task(
        iam_client,
        ssm_client,
        mock_subprocess,
        mock_application,
        env,
        addon_type,
        addon_name,
        task_name,
        access,
    )

    mock_subprocess.call.assert_called()
    mock_subprocess.call.assert_called_once_with(
        f"copilot task run --app test-application --env {env} "
        f"--task-group-name {task_name} "
        f"--execution-role {addon_name}-{mock_application.name}-{env}-conduitEcsTask "
        f"--image public.ecr.aws/uktrade/tunnel:{addon_type} "
        "--secrets CONNECTION_SECRET=test-arn "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


@pytest.mark.parametrize(
    "access",
    [
        "read",
        "write",
    ],
)
@patch(
    "dbt_platform_helper.providers.secrets.Secrets.get_connection_secret_arn",
    return_value="test-arn",
)
def test_create_postgres_addon_client_task(
    get_connection_secret_arn,
    access,
):

    addon_name = "custom-name-postgres"
    addon_type = "postgres"
    mock_application = Mock()
    mock_application.name = "test-application"
    mock_application.environments = {"development": Mock()}
    task_name = mock_task_name(addon_name)
    mock_subprocess = Mock()

    iam_client = mock_application.environments[env].session.client("iam")
    ssm_client = mock_application.environments[env].session.client("ssm")

    create_addon_client_task(
        iam_client,
        ssm_client,
        mock_subprocess,
        mock_application,
        env,
        "postgres",
        addon_name,
        task_name,
        access,
    )
    secret_name = expected_connection_secret_name(mock_application, addon_type, addon_name, access)
    get_connection_secret_arn.assert_called_once_with(secret_name)
    mock_subprocess.call.assert_called()
    mock_subprocess.call.assert_called_once_with(
        f"copilot task run --app test-application --env {env} "
        f"--task-group-name {task_name} "
        f"--execution-role {addon_name}-{mock_application.name}-{env}-conduitEcsTask "
        f"--image public.ecr.aws/uktrade/tunnel:{addon_type} "
        "--secrets CONNECTION_SECRET=test-arn "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


@patch("dbt_platform_helper.providers.copilot.create_postgres_admin_task")
def test_create_postgres_addon_client_task_admin(
    mock_create_postgres_admin_task,
    mock_application,
):

    addon_name = "custom-name-postgres"
    task_name = mock_task_name(addon_name)
    mock_subprocess = Mock()

    iam_client = mock_application.environments[env].session.client("iam")
    ssm_client = mock_application.environments[env].session.client("ssm")
    create_addon_client_task(
        iam_client,
        ssm_client,
        mock_subprocess,
        mock_application,
        env,
        "postgres",
        addon_name,
        task_name,
        "admin",
    )
    secret_name = expected_connection_secret_name(mock_application, "postgres", addon_name, "admin")

    mock_create_postgres_admin_task.assert_called_once_with(
        ssm_client,
        mock_subprocess,
        mock_application,
        addon_name,
        "postgres",
        env,
        secret_name,
        task_name,
    )


@patch(
    "dbt_platform_helper.providers.secrets.Secrets.get_connection_secret_arn",
    return_value="test-arn",
)
def test_create_addon_client_task_does_not_add_execution_role_if_role_not_found(
    get_connection_secret_arn,
    mock_application,
):
    """Test that, given app, env and permissions, create_addon_client_task calls
    get_connection_secret_arn with the default secret name and subsequently
    subprocess.call with the correct secret ARN but no execution role."""

    addon_name = "postgres"
    addon_type = "custom-name-postgres"
    access = "read"
    mock_subprocess = Mock()
    mock_application.environments[env] = Mock()
    mock_application.environments[env].session.client.return_value = Mock()
    mock_application.environments[env].session.client.return_value.get_role.side_effect = (
        NoSuchEntityException()
    )
    task_name = mock_task_name(addon_name)

    ssm_client = mock_application.environments[env].session.client("ssm")

    create_addon_client_task(
        mock_application.environments[env].session.client("iam"),
        ssm_client,
        mock_subprocess,
        mock_application,
        env,
        addon_type,
        addon_name,
        task_name,
        access,
    )

    secret_name = expected_connection_secret_name(mock_application, addon_type, addon_name, access)
    get_connection_secret_arn.assert_called_once_with(secret_name)

    mock_subprocess.call.assert_called_once_with(
        f"copilot task run --app test-application --env {env} "
        f"--task-group-name {task_name} "
        f"--image public.ecr.aws/uktrade/tunnel:{addon_type} "
        "--secrets CONNECTION_SECRET=test-arn "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


@patch("click.secho")
def test_create_addon_client_task_abort_with_message_on_other_exceptions(
    mock_secho,
    mock_application,
):
    """Test that if an unexpected ClientError is throw when trying to get the
    execution role, create_addon_client_task aborts with a message."""

    addon_name = "postgres"
    addon_type = "custom-name-postgres"
    access = "read"
    mock_subprocess = Mock()
    mock_application.environments[env] = Mock()
    mock_application.environments[env].session.client.return_value = Mock()
    mock_application.environments[env].session.client.return_value.get_role.side_effect = (
        ClientError(
            operation_name="something_else",
            error_response={"Error": {"Message": "Something went wrong"}},
        )
    )
    task_name = mock_task_name(addon_name)
    iam_client = mock_application.environments[env].session.client("iam")
    ssm_client = mock_application.environments[env].session.client("ssm")

    with pytest.raises(SystemExit) as exc_info:
        create_addon_client_task(
            iam_client,
            ssm_client,
            mock_subprocess,
            mock_application,
            env,
            addon_type,
            addon_name,
            task_name,
            access,
        )

    assert exc_info.value.code == 1
    assert mock_secho.call_count > 0
    assert (
        mock_secho.call_args[0][0]
        == f"Error: cannot obtain Role {addon_name}-{mock_application.name}-{env}-conduitEcsTask: Something went wrong"
    )


@patch("dbt_platform_helper.providers.secrets.Secrets.get_connection_secret_arn")
def test_create_addon_client_task_when_no_secret_found(get_connection_secret_arn):
    """Test that, given app, environment and secret name strings,
    create_addon_client_task raises a NoConnectionSecretError and does not call
    subprocess.call."""

    mock_application = Mock()
    mock_application.name = "test-application"
    mock_application.environments = {"development": Mock()}
    mock_subprocess = Mock()
    iam_client = mock_application.environments[env].session.client("iam")
    ssm_client = mock_application.environments[env].session.client("ssm")

    get_connection_secret_arn.side_effect = SecretNotFoundException(
        "/copilot/test-application/development/secrets/named-postgres"
    )

    with pytest.raises(SecretNotFoundException):
        create_addon_client_task(
            iam_client,
            ssm_client,
            mock_subprocess,
            mock_application,
            env,
            "postgres",
            "named-postgres",
            mock_task_name("named-postgres"),
            "read",
        )

        mock_subprocess.call.assert_not_called()


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_connect_to_addon_client_task(addon_type, mock_application):
    """
    Test that, given app, env, ECS cluster ARN and addon type,
    connect_to_addon_client_task calls addon_client_is_running with cluster ARN
    and addon type.

    It then subsequently calls subprocess.call with the correct app, env and
    addon type.
    """

    task_name = mock_task_name(addon_type)
    ecs_client = mock_application.environments[env].session.client("ecs")
    mock_subprocess = Mock()
    addon_client_is_running = Mock(return_value=True)

    connect_to_addon_client_task(
        ecs_client,
        mock_subprocess,
        mock_application.name,
        env,
        "test-arn",
        task_name,
        addon_client_is_running,
    )

    addon_client_is_running.assert_called_once_with(ecs_client, "test-arn", task_name)
    mock_subprocess.call.assert_called_once_with(
        f"copilot task exec --app test-application --env {env} "
        f"--name {task_name} "
        f"--command bash",
        shell=True,
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("time.sleep", return_value=None)
def test_connect_to_addon_client_task_with_timeout_reached_throws_exception(
    sleep, addon_type, mock_application
):
    """Test that, given app, env, ECS cluster ARN and addon type, when the
    client agent fails to start, connect_to_addon_client_task calls
    addon_client_is_running with cluster ARN and addon type 15 times, but does
    not call subprocess.call."""

    task_name = mock_task_name(addon_type)
    ecs_client = mock_application.environments[env].session.client("ecs")
    mock_subprocess = Mock()
    get_ecs_task_arns = Mock(return_value=[])

    with pytest.raises(CreateTaskTimeoutException):
        connect_to_addon_client_task(
            ecs_client,
            mock_subprocess,
            mock_application,
            env,
            "test-arn",
            task_name,
            get_ecs_task_arns=get_ecs_task_arns,
        )

    get_ecs_task_arns.assert_called_with(ecs_client, "test-arn", task_name)
    assert get_ecs_task_arns.call_count == 15
    mock_subprocess.call.assert_not_called()
