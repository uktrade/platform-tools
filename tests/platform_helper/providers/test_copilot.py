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
from dbt_platform_helper.exceptions import ParameterNotFoundError
from dbt_platform_helper.providers.copilot import CreateTaskTimeoutError
from dbt_platform_helper.providers.copilot import connect_to_addon_client_task
from dbt_platform_helper.providers.copilot import create_addon_client_task
from dbt_platform_helper.providers.copilot import create_postgres_admin_task
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

    get_connection_secret_arn.side_effect = SecretNotFoundError(
        "/copilot/test-application/development/secrets/named-postgres"
    )

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


# @mock_aws TODO!
# @patch("dbt_platform_helper.providers.ecs.ecs_exec_is_available", side_effect=ECSAgentNotRunning)
# def test_connect_to_addon_client_task_waits_for_command_agent(ecs_exec_is_available, mock_cluster_client_task, mocked_cluster, mock_application):
#     task_name = mock_task_name("postgres")
#     mock_cluster_client_task("postgres")
#     mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
#     ecs_client = mock_application.environments["development"].session.client("ecs")
#     mock_subprocess = Mock()
#     # We want this to throw InvalidParameterException the first time, then behave as normal

#     with pytest.raises(ECSAgentNotRunning):
#         connect_to_addon_client_task(
#             ecs_client, mock_subprocess, mock_application.name, env, mocked_cluster_arn, task_name
#         )
#     # Assert "Unable to connect, execute command agent probably isn’t running yet" in output
#     # If it doesn't bomb out with CreateTaskTimeoutError all is good


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
    get_ecs_task_arns = Mock(return_value=False)

    with pytest.raises(CreateTaskTimeoutError):
        connect_to_addon_client_task(
            ecs_client,
            mock_subprocess,
            mock_application,
            env,
            "test-arn",
            task_name,
            get_ecs_task_arns_fn=get_ecs_task_arns,
        )

    get_ecs_task_arns.assert_called_with(ecs_client, "test-arn", task_name)
    assert get_ecs_task_arns.call_count == 15
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
