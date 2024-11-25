import json
from unittest.mock import Mock
from unittest.mock import patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from dbt_platform_helper.exceptions import AddonNotFoundError
from dbt_platform_helper.exceptions import AddonTypeMissingFromConfigError
from dbt_platform_helper.exceptions import InvalidAddonTypeError
from dbt_platform_helper.exceptions import NoClusterError
from dbt_platform_helper.exceptions import ParameterNotFoundError
from dbt_platform_helper.providers.copilot import CreateTaskTimeoutError
from dbt_platform_helper.providers.copilot import connect_to_addon_client_task
from dbt_platform_helper.providers.copilot import create_addon_client_task
from dbt_platform_helper.providers.copilot import create_postgres_admin_task
from dbt_platform_helper.providers.ecs import addon_client_is_running
from dbt_platform_helper.providers.ecs import get_cluster_arn
from dbt_platform_helper.providers.ecs import get_or_create_task_name
from dbt_platform_helper.providers.secrets import SecretNotFoundError
from dbt_platform_helper.providers.secrets import (
    _normalise_secret_name as normalise_secret_name,
)
from dbt_platform_helper.providers.secrets import get_addon_type
from dbt_platform_helper.providers.secrets import get_parameter_name
from tests.platform_helper.conftest import NoSuchEntityException
from tests.platform_helper.conftest import add_addon_config_parameter
from tests.platform_helper.conftest import expected_connection_secret_name
from tests.platform_helper.conftest import mock_parameter_name
from tests.platform_helper.conftest import mock_task_name

env = "development"


@pytest.mark.parametrize(
    "test_string",
    [
        ("app-rds-postgres", "APP_RDS_POSTGRES"),
        ("APP-POSTGRES", "APP_POSTGRES"),
        ("APP-OpenSearch", "APP_OPENSEARCH"),
    ],
)
def test_normalise_secret_name(test_string):
    """Test that given an addon name, normalise_secret_name produces the
    expected result."""

    assert normalise_secret_name(test_string[0]) == test_string[1]


@mock_aws
def test_get_cluster_arn(mocked_cluster, mock_application):
    """Test that, given app and environment strings, get_cluster_arn returns the
    arn of a cluster tagged with these strings."""

    assert (
        get_cluster_arn(
            mock_application.environments[env].session.client("ecs"), mock_application.name, env
        )
        == mocked_cluster["cluster"]["clusterArn"]
    )


@mock_aws
def test_get_cluster_arn_when_there_is_no_cluster(mock_application):
    """Test that, given app and environment strings, get_cluster_arn raises an
    exception when no cluster tagged with these strings exists."""

    env = "staging"

    with pytest.raises(NoClusterError):
        get_cluster_arn(
            mock_application.environments[env].session.client("ecs"), mock_application.name, env
        )


@mock_aws
@patch(  # Nested function within provider function
    "dbt_platform_helper.providers.copilot.get_postgres_connection_data_updated_with_master_secret",
    return_value="connection string",
)
def test_create_postgres_admin_task(mock_update_parameter, mock_application):

    addon_name = "dummy-postgres"
    master_secret_name = f"/copilot/{mock_application.name}/{env}/secrets/{normalise_secret_name(addon_name)}_RDS_MASTER_ARN"
    ssm_client = mock_application.environments[env].session.client("ssm")
    secrets_manager_client = mock_application.environments[env].session.client("secretsmanager")

    boto3.client("ssm").put_parameter(
        Name=master_secret_name, Value="master-secret-arn", Type="String"
    )
    mock_subprocess = Mock()

    create_postgres_admin_task(
        ssm_client,
        secrets_manager_client,
        mock_subprocess,
        mock_application,
        addon_name,
        "postgres",
        env,
        "POSTGRES_SECRET_NAME",
        "test-task",
    )

    mock_update_parameter.assert_called_once_with(
        ssm_client,
        secrets_manager_client,
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
@patch("dbt_platform_helper.providers.copilot.get_connection_secret_arn", return_value="test-arn")
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
    secretsmanager_client = mock_application.environments[env].session.client("secretsmanager")

    create_addon_client_task(
        iam_client,
        ssm_client,
        secretsmanager_client,
        mock_subprocess,
        mock_application,
        env,
        addon_type,
        addon_name,
        task_name,
        access,
    )

    secret_name = expected_connection_secret_name(mock_application, addon_type, addon_name, access)
    get_connection_secret_arn.assert_called_once_with(
        ssm_client, secretsmanager_client, secret_name
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
@patch("dbt_platform_helper.providers.copilot.get_connection_secret_arn", return_value="test-arn")
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
    secretsmanager_client = mock_application.environments[env].session.client("secretsmanager")

    create_addon_client_task(
        iam_client,
        ssm_client,
        secretsmanager_client,
        mock_subprocess,
        mock_application,
        env,
        "postgres",
        addon_name,
        task_name,
        access,
    )
    secret_name = expected_connection_secret_name(mock_application, addon_type, addon_name, access)
    get_connection_secret_arn.assert_called_once_with(
        ssm_client, secretsmanager_client, secret_name
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
    secretsmanager_client = mock_application.environments[env].session.client("secretsmanager")
    create_addon_client_task(
        iam_client,
        ssm_client,
        secretsmanager_client,
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
        secretsmanager_client,
        mock_subprocess,
        mock_application,
        addon_name,
        "postgres",
        env,
        secret_name,
        task_name,
    )


@patch("dbt_platform_helper.providers.copilot.get_connection_secret_arn", return_value="test-arn")
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
    secretsmanager_client = mock_application.environments[env].session.client("secretsmanager")

    create_addon_client_task(
        mock_application.environments[env].session.client("iam"),
        ssm_client,
        secretsmanager_client,
        mock_subprocess,
        mock_application,
        env,
        addon_type,
        addon_name,
        task_name,
        access,
    )

    secret_name = expected_connection_secret_name(mock_application, addon_type, addon_name, access)
    get_connection_secret_arn.assert_called_once_with(
        ssm_client, secretsmanager_client, secret_name
    )

    mock_subprocess.call.assert_called_once_with(
        f"copilot task run --app test-application --env {env} "
        f"--task-group-name {task_name} "
        f"--image public.ecr.aws/uktrade/tunnel:{addon_type} "
        "--secrets CONNECTION_SECRET=test-arn "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


@patch("dbt_platform_helper.providers.copilot.get_connection_secret_arn", return_value="test-arn")
@patch("click.secho")
def test_create_addon_client_task_abort_with_message_on_other_exceptions(
    mock_secho,
    get_connection_secret_arn,
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
    secretsmanager_client = mock_application.environments[env].session.client("secretsmanager")

    with pytest.raises(SystemExit) as exc_info:
        create_addon_client_task(
            iam_client,
            ssm_client,
            secretsmanager_client,
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


@patch("dbt_platform_helper.providers.copilot.get_connection_secret_arn")
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
    secretsmanager_client = mock_application.environments[env].session.client("secretsmanager")

    get_connection_secret_arn.side_effect = SecretNotFoundError

    with pytest.raises(SecretNotFoundError):
        create_addon_client_task(
            iam_client,
            ssm_client,
            secretsmanager_client,
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
def test_addon_client_is_running(
    mock_cluster_client_task, mocked_cluster, addon_type, mock_application
):
    """Test that, given cluster ARN, addon type and with a running agent,
    addon_client_is_running returns True."""

    mocked_cluster_for_client = mock_cluster_client_task(addon_type)
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    ecs_client = mock_application.environments[env].session.client("ecs")

    with patch(
        "dbt_platform_helper.utils.application.boto3.client", return_value=mocked_cluster_for_client
    ):
        assert addon_client_is_running(ecs_client, mocked_cluster_arn, mock_task_name(addon_type))


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_addon_client_is_running_when_no_client_task_running(
    mock_cluster_client_task, mocked_cluster, addon_type, mock_application
):
    """Test that, given cluster ARN, addon type and without a running client
    task, addon_client_is_running returns False."""

    mocked_cluster_for_client = mock_cluster_client_task(addon_type, task_running=False)
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    ecs_client = mock_application.environments[env].session.client("ecs")

    with patch(
        "dbt_platform_helper.utils.application.boto3.client", return_value=mocked_cluster_for_client
    ):
        assert (
            addon_client_is_running(ecs_client, mocked_cluster_arn, mock_task_name(addon_type))
            is False
        )


@mock_aws
@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_addon_client_is_running_when_no_client_agent_running(
    addon_type, mock_application, mocked_cluster
):
    ecs_client = mock_application.environments[env].session.client("ecs")
    cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    task_name = "some-task-name"
    ec2 = boto3.resource("ec2")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    mocked_task_definition_arn = ecs_client.register_task_definition(
        family=f"copilot-foobar",
        requiresCompatibilities=["FARGATE"],
        networkMode="awsvpc",
        containerDefinitions=[
            {
                "name": "test_container",
                "image": "test_image",
                "cpu": 256,
                "memory": 512,
                "essential": True,
            }
        ],
    )["taskDefinition"]["taskDefinitionArn"]
    ecs_client.run_task(
        taskDefinition=mocked_task_definition_arn,
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": [subnet.id],
                "securityGroups": ["something-sg"],
            }
        },
    )

    assert addon_client_is_running(ecs_client, cluster_arn, task_name) is False


@mock_aws
def test_get_or_create_task_name(mock_application):
    """Test that get_or_create_task_name retrieves the task name from the
    parameter store when it has been stored."""

    addon_name = "app-postgres"
    parameter_name = mock_parameter_name(mock_application, "postgres", addon_name)
    mock_application.environments[env].session.client("ssm")
    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name=parameter_name,
        Type="String",
        Value=mock_task_name(addon_name),
    )

    task_name = get_or_create_task_name(
        mock_ssm, mock_application.name, env, addon_name, parameter_name
    )

    assert task_name == mock_task_name(addon_name)


@mock_aws
def test_get_or_create_task_name_when_name_does_not_exist(mock_application):
    """Test that get_or_create_task_name creates the task name and appends it
    with a 12 digit lowercase alphanumeric string when it does not exist in the
    parameter store."""

    addon_name = "app-postgres"
    ssm_client = mock_application.environments[env].session.client("ssm")
    parameter_name = mock_parameter_name(mock_application, "postgres", addon_name)
    task_name = get_or_create_task_name(
        ssm_client, mock_application.name, env, addon_name, parameter_name
    )
    random_id = task_name.rsplit("-", 1)[1]

    assert task_name.rsplit("-", 1)[0] == mock_task_name("app-postgres").rsplit("-", 1)[0]
    assert random_id.isalnum() and random_id.islower() and len(random_id) == 12


@mock_aws
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
        ("postgres", "custom-name-postgres"),
        ("postgres", "custom-name-rds-postgres"),
        ("redis", "custom-name-redis"),
        ("opensearch", "custom-name-opensearch"),
        ("s3", "custon-name-s3"),
    ],
)
def test_get_parameter_name(access, addon_type, addon_name, mock_application):
    """Test that get_parameter_name builds the correct parameter name given the
    addon_name, addon_type and permission."""

    parameter_name = get_parameter_name(
        mock_application.name, "development", addon_type, addon_name, access
    )
    assert parameter_name == mock_parameter_name(mock_application, addon_type, addon_name, access)


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_platform_helper.providers.copilot.addon_client_is_running", return_value=True)
def test_connect_to_addon_client_task(addon_client_is_running, addon_type, mock_application):
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

    connect_to_addon_client_task(
        ecs_client, mock_subprocess, mock_application.name, env, "test-arn", task_name
    )

    addon_client_is_running.assert_called_once_with(ecs_client, "test-arn", task_name)
    mock_subprocess.call.assert_called_once_with(
        f"copilot task exec --app test-application --env {env} "
        f"--name {task_name} "
        f"--command bash",
        shell=True,
    )


# Todo: Implement this test
# @patch("dbt_platform_helper.providers.copilot.addon_client_is_running", return_value=True)
# def test_connect_to_addon_client_task_waits_for_command_agent(addon_client_is_running, mock_application):
#     task_name = mock_task_name("postgres") # Addon type for this test does not matter
#     ecs_client = mock_application.environments[env].session.client("ecs")
#     mock_subprocess = Mock()
#     # We want this to throw InvalidParameterException the first time, then behave as normal
#
#     connect_to_addon_client_task(
#         ecs_client, mock_subprocess, mock_application.name, env, "test-arn", task_name
#     )
#
#     # Assert "Unable to connect, execute command agent probably isn’t running yet" in output
#     # If it doesn't bomb out with CreateTaskTimeoutError all is good


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("time.sleep", return_value=None)
@patch("dbt_platform_helper.providers.copilot.addon_client_is_running", return_value=False)
def test_connect_to_addon_client_task_with_timeout_reached_throws_exception(
    addon_client_is_running, sleep, addon_type, mock_application
):
    """Test that, given app, env, ECS cluster ARN and addon type, when the
    client agent fails to start, connect_to_addon_client_task calls
    addon_client_is_running with cluster ARN and addon type 15 times, but does
    not call subprocess.call."""

    task_name = mock_task_name(addon_type)
    ecs_client = mock_application.environments[env].session.client("ecs")
    mock_subprocess = Mock()

    with pytest.raises(CreateTaskTimeoutError):
        connect_to_addon_client_task(
            ecs_client, mock_subprocess, mock_application, env, "test-arn", task_name
        )

    addon_client_is_running.assert_called_with(ecs_client, "test-arn", task_name)
    assert addon_client_is_running.call_count == 15
    mock_subprocess.call.assert_not_called()


@mock_aws
@pytest.mark.parametrize(
    "addon_name, expected_type",
    [
        ("custom-name-postgres", "postgres"),
        ("custom-name-redis", "redis"),
        ("custom-name-opensearch", "opensearch"),
    ],
)
def test_get_addon_type(addon_name, expected_type, mock_application):
    """Test that get_addon_type returns the expected addon type."""

    ssm_client = mock_application.environments[env].session.client("ssm")

    add_addon_config_parameter()
    addon_type = get_addon_type(ssm_client, mock_application.name, env, addon_name)

    assert addon_type == expected_type


@mock_aws
def test_get_addon_type_with_not_found_throws_exception(mock_application):
    """Test that get_addon_type raises the expected error when the addon is not
    found in the config file."""

    add_addon_config_parameter({"different-name": {"type": "redis"}})
    ssm_client = mock_application.environments[env].session.client("ssm")

    with pytest.raises(AddonNotFoundError):
        get_addon_type(ssm_client, mock_application.name, env, "custom-name-postgres")


@mock_aws
def test_get_addon_type_with_parameter_not_found_throws_exception(mock_application):
    """Test that get_addon_type raises the expected error when the addon config
    parameter is not found."""

    ssm_client = mock_application.environments[env].session.client("ssm")

    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name=f"/copilot/applications/test-application/environments/development/invalid-parameter",
        Type="String",
        Value=json.dumps({"custom-name-postgres": {"type": "postgres"}}),
    )

    with pytest.raises(ParameterNotFoundError):
        get_addon_type(ssm_client, mock_application.name, env, "custom-name-postgres")


@mock_aws
def test_get_addon_type_with_invalid_type_throws_exception(mock_application):
    """Test that get_addon_type raises the expected error when the config
    contains an invalid addon type."""

    add_addon_config_parameter(param_value={"invalid-extension": {"type": "invalid"}})
    ssm_client = mock_application.environments[env].session.client("ssm")

    with pytest.raises(InvalidAddonTypeError):
        get_addon_type(ssm_client, mock_application.name, env, "invalid-extension")


@mock_aws
def test_get_addon_type_with_blank_type_throws_exception(mock_application):
    """Test that get_addon_type raises the expected error when the config
    contains an empty addon type."""

    add_addon_config_parameter(param_value={"blank-extension": {}})
    ssm_client = mock_application.environments[env].session.client("ssm")

    with pytest.raises(AddonTypeMissingFromConfigError):
        get_addon_type(ssm_client, mock_application.name, env, "blank-extension")


@mock_aws
def test_get_addon_type_with_unspecified_type_throws_exception(mock_application):
    """Test that get_addon_type raises the expected error when the config
    contains an empty addon type."""

    add_addon_config_parameter(param_value={"addon-type-unspecified": {"type": None}})
    ssm_client = mock_application.environments[env].session.client("ssm")

    with pytest.raises(AddonTypeMissingFromConfigError):
        get_addon_type(ssm_client, mock_application.name, env, "addon-type-unspecified")
