import json
from unittest.mock import Mock
from unittest.mock import patch

import boto3
import pytest
from cfn_tools import load_yaml
from click.testing import CliRunner
from moto import mock_cloudformation
from moto import mock_ecs
from moto import mock_iam
from moto import mock_resourcegroupstaggingapi
from moto import mock_secretsmanager
from moto import mock_ssm

from tests.copilot_helper.conftest import mock_task_name


@pytest.mark.parametrize(
    "test_string",
    [
        ("app-rds-postgres", "APP_RDS_POSTGRES"),
        ("APP-POSTGRES", "APP_POSTGRES"),
        ("APP-OpenSearch", "APP_OPENSEARCH"),
    ],
)
def test_get_secret_name(test_string):
    """Test that given an addon name, get_secret_name produces the expected
    result."""
    from dbt_copilot_helper.commands.conduit import get_secret_name

    assert get_secret_name(test_string[0]) == test_string[1]


@mock_resourcegroupstaggingapi
def test_get_cluster_arn(mocked_cluster, mock_application):
    """Test that, given app and environment strings, get_cluster_arn returns the
    arn of a cluster tagged with these strings."""
    from dbt_copilot_helper.commands.conduit import get_cluster_arn

    assert (
        get_cluster_arn(mock_application, "development") == mocked_cluster["cluster"]["clusterArn"]
    )


@mock_ecs
def test_get_cluster_arn_when_there_is_no_cluster(mock_application):
    """Test that, given app and environment strings, get_cluster_arn raises an
    exception when no cluster tagged with these strings exists."""
    from dbt_copilot_helper.commands.conduit import NoClusterConduitError
    from dbt_copilot_helper.commands.conduit import get_cluster_arn

    with pytest.raises(NoClusterConduitError):
        get_cluster_arn(mock_application, "staging")


@mock_secretsmanager
@mock_ssm
def test_get_connection_secret_arn_from_secrets_manager(mock_application):
    """Test that, given app, environment and secret name strings,
    get_connection_secret_arn returns an ARN from secrets manager."""
    from dbt_copilot_helper.commands.conduit import get_connection_secret_arn

    mock_secretsmanager = boto3.client("secretsmanager")
    mock_secretsmanager.create_secret(
        Name="/copilot/test-application/development/secrets/POSTGRES",
        SecretString="something-secret",
    )

    arn = get_connection_secret_arn(mock_application, "development", "POSTGRES")

    assert arn.startswith(
        "arn:aws:secretsmanager:eu-west-2:123456789012:secret:"
        "/copilot/test-application/development/secrets/POSTGRES-"
    )


@mock_ssm
def test_get_connection_secret_arn_from_parameter_store(mock_application):
    """Test that, given app, environment and secret name strings,
    get_connection_secret_arn returns an ARN from parameter store."""
    from dbt_copilot_helper.commands.conduit import get_connection_secret_arn

    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name="/copilot/test-application/development/secrets/POSTGRES",
        Value="something-secret",
        Type="SecureString",
    )

    arn = get_connection_secret_arn(mock_application, "development", "POSTGRES")

    assert (
        arn
        == "arn:aws:ssm:eu-west-2:123456789012:parameter/copilot/test-application/development/secrets/POSTGRES"
    )


@mock_secretsmanager
@mock_ssm
def test_get_connection_secret_arn_when_secret_does_not_exist(mock_application):
    """Test that, given app, environment and secret name strings,
    get_connection_secret_arn raises an exception when no matching secret exists
    in secrets manager or parameter store."""
    from dbt_copilot_helper.commands.conduit import SecretNotFoundConduitError
    from dbt_copilot_helper.commands.conduit import get_connection_secret_arn

    with pytest.raises(SecretNotFoundConduitError):
        get_connection_secret_arn(mock_application, "development", "POSTGRES")


@patch("subprocess.call")
@patch("dbt_copilot_helper.commands.conduit.get_connection_secret_arn", return_value="test-arn")
def test_create_addon_client_task(get_connection_secret_arn, subprocess_call, mock_application):
    """Test that, given app and environment strings, create_addon_client_task
    calls get_connection_secret_arn with the default secret name and
    subsequently subprocess.call with the correct secret ARN."""
    from dbt_copilot_helper.commands.conduit import create_addon_client_task

    addon_name = "custom-name-postgres"
    task_name = mock_task_name(addon_name)
    create_addon_client_task(mock_application, "development", "postgres", addon_name, task_name)

    get_connection_secret_arn.assert_called_once_with(mock_application, "development", addon_name)
    subprocess_call.assert_called_once_with(
        "copilot task run --app test-application --env development "
        f"--task-group-name {task_name} "
        "--image public.ecr.aws/uktrade/tunnel:postgres "
        "--secrets CONNECTION_SECRET=test-arn "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


@patch("subprocess.call")
@patch(
    "dbt_copilot_helper.commands.conduit.get_connection_secret_arn", return_value="test-named-arn"
)
def test_create_addon_client_task_with_addon_name(
    get_connection_secret_arn, subprocess_call, mock_application
):
    """Test that, given app, environment and secret name strings,
    create_addon_client_task calls get_connection_secret_arn with the custom
    secret name and subsequently subprocess.call with the correct secret ARN."""
    from dbt_copilot_helper.commands.conduit import create_addon_client_task

    addon_name = "custom-name-postgres"
    task_name = mock_task_name(addon_name)
    create_addon_client_task(mock_application, "development", "postgres", addon_name, task_name)

    get_connection_secret_arn.assert_called_once_with(mock_application, "development", addon_name)
    subprocess_call.assert_called_once_with(
        "copilot task run --app test-application --env development "
        f"--task-group-name {task_name} "
        "--image public.ecr.aws/uktrade/tunnel:postgres "
        "--secrets CONNECTION_SECRET=test-named-arn "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


@patch("subprocess.call")
@patch("dbt_copilot_helper.commands.conduit.get_connection_secret_arn")
def test_create_addon_client_task_when_no_secret_found(
    get_connection_secret_arn, subprocess_call, mock_application
):
    """Test that, given app, environment and secret name strings,
    create_addon_client_task raises a NoConnectionSecretError and does not call
    subprocess.call."""
    from dbt_copilot_helper.commands.conduit import SecretNotFoundConduitError
    from dbt_copilot_helper.commands.conduit import create_addon_client_task

    get_connection_secret_arn.side_effect = SecretNotFoundConduitError

    with pytest.raises(SecretNotFoundConduitError):
        create_addon_client_task(
            mock_application,
            "development",
            "postgres",
            "named-postgres",
            mock_task_name("named-postgres"),
        )

        subprocess_call.assert_not_called()


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_addon_client_is_running(
    mock_cluster_client_task, mocked_cluster, addon_type, mock_application
):
    """Test that, given cluster ARN, addon type and with a running agent,
    addon_client_is_running returns True."""
    from dbt_copilot_helper.commands.conduit import addon_client_is_running

    mocked_cluster_for_client = mock_cluster_client_task(addon_type)
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]

    with patch(
        "dbt_copilot_helper.utils.application.boto3.client", return_value=mocked_cluster_for_client
    ):
        assert addon_client_is_running(
            mock_application, "development", mocked_cluster_arn, mock_task_name(addon_type)
        )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_addon_client_is_running_when_no_client_task_running(
    mock_cluster_client_task, mocked_cluster, addon_type, mock_application
):
    """Test that, given cluster ARN, addon type and without a running client
    task, addon_client_is_running returns False."""
    from dbt_copilot_helper.commands.conduit import addon_client_is_running

    mocked_cluster_for_client = mock_cluster_client_task(addon_type, task_running=False)
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]

    with patch(
        "dbt_copilot_helper.utils.application.boto3.client", return_value=mocked_cluster_for_client
    ):
        assert (
            addon_client_is_running(
                mock_application, "development", mocked_cluster_arn, mock_task_name(addon_type)
            )
            is False
        )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_addon_client_is_running_when_no_client_agent_running(
    mock_cluster_client_task, mocked_cluster, addon_type, mock_application
):
    """Test that, given cluster ARN, addon type and without a running agent,
    addon_client_is_running returns False."""
    from dbt_copilot_helper.commands.conduit import addon_client_is_running

    mocked_cluster_for_client = mock_cluster_client_task(addon_type, "ACTIVATING")
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]

    with patch(
        "dbt_copilot_helper.utils.application.boto3.client", return_value=mocked_cluster_for_client
    ):
        assert (
            addon_client_is_running(
                mock_application, "development", mocked_cluster_arn, mock_task_name(addon_type)
            )
            is False
        )


@mock_iam
@mock_cloudformation
@pytest.mark.parametrize(
    "addon_name",
    ["postgres", "redis", "opensearch", "rds-postgres"],
)
@patch("time.sleep", return_value=None)
def test_add_stack_delete_policy_to_task_role(sleep, mock_stack, addon_name, mock_application):
    """Test that, given app, env and addon name
    add_stack_delete_policy_to_task_role adds a policy to the IAM role in a
    CloudFormation stack."""
    from dbt_copilot_helper.commands.conduit import add_stack_delete_policy_to_task_role

    task_name = mock_task_name(addon_name)
    stack_name = f"task-{task_name}"

    mock_stack(addon_name)
    mock_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": ["cloudformation:DeleteStack"],
                "Effect": "Allow",
                "Resource": f"arn:aws:cloudformation:*:*:stack/{stack_name}/*",
            },
        ],
    }

    add_stack_delete_policy_to_task_role(mock_application, "development", task_name)

    stack_resources = boto3.client("cloudformation").list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]

    policy_name = None
    policy_document = None
    for resource in stack_resources:
        if resource["LogicalResourceId"] == "DefaultTaskRole":
            policy = boto3.client("iam").get_role_policy(
                RoleName=resource["PhysicalResourceId"], PolicyName="DeleteCloudFormationStack"
            )
            policy_name = policy["PolicyName"]
            policy_document = policy["PolicyDocument"]

    assert policy_name == "DeleteCloudFormationStack"
    assert policy_document == mock_policy


@mock_iam
@mock_ssm
@mock_cloudformation
@pytest.mark.parametrize(
    "addon_type, addon_name",
    [
        ("postgres", "custom-name-postgres"),
        ("postgres", "custom-name-rds-postgres"),
        ("redis", "custom-name-redis"),
        ("opensearch", "custom-name-opensearch"),
    ],
)
def test_update_conduit_stack_resources(mock_stack, addon_type, addon_name, mock_application):
    """Test that, given app, env and addon name update_conduit_stack_resources
    updates the conduit CloudFormation stack to add DeletionPolicy:Retain and
    subscription filter to the LogGroup."""
    from dbt_copilot_helper.commands.conduit import update_conduit_stack_resources

    boto3.client("iam").create_role(
        RoleName="CWLtoSubscriptionFilterRole",
        AssumeRolePolicyDocument="123",
    )

    boto3.client("ssm").put_parameter(
        Name="/copilot/tools/central_log_groups",
        Value=json.dumps(
            {
                "prod": "arn:aws:logs:eu-west-2:prod_account_id:destination:test_log_destination",
                "dev": "arn:aws:logs:eu-west-2:dev_account_id:destination:test_log_destination",
            }
        ),
        Type="String",
    )

    mock_stack(addon_name)
    task_name = mock_task_name(addon_name)

    update_conduit_stack_resources(
        mock_application, "development", addon_type, addon_name, task_name
    )

    template = boto3.client("cloudformation").get_template(StackName=f"task-{task_name}")
    template_yml = load_yaml(template["TemplateBody"])
    assert template_yml["Resources"]["LogGroup"]["DeletionPolicy"] == "Retain"
    assert (
        template_yml["Resources"]["TaskNameParameter"]["Properties"]["Name"]
        == f"/copilot/{mock_application.name}/development/conduits/{addon_name.replace('-', '_').upper()}_CONDUIT_TASK_NAME"
    )
    assert (
        template_yml["Resources"]["SubscriptionFilter"]["Properties"]["LogGroupName"]
        == f"/copilot/{task_name}"
    )
    assert (
        "dev_account_id"
        in template_yml["Resources"]["SubscriptionFilter"]["Properties"]["DestinationArn"]
    )
    assert (
        template_yml["Resources"]["SubscriptionFilter"]["Properties"]["FilterName"]
        == f"/copilot/conduit/{mock_application.name}/development/{addon_type}/{addon_name}/{task_name.rsplit('-', 1)[1]}"
    )


@mock_ssm
def test_get_or_create_task_name(mock_application):
    """Test that get_or_create_task_name retrieves the task name from the
    parameter store when it has been stored."""
    from dbt_copilot_helper.commands.conduit import get_or_create_task_name

    addon_name = "app-postgres"
    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name=f"/copilot/test-application/development/conduits/{addon_name.replace('-', '_').upper()}_CONDUIT_TASK_NAME",
        Type="String",
        Value=mock_task_name(addon_name),
    )

    task_name = get_or_create_task_name(mock_application, "development", addon_name)

    assert task_name == mock_task_name(addon_name)


@mock_ssm
def test_get_or_create_task_name_when_name_does_not_exist(mock_application):
    """Test that get_or_create_task_name creates the task name and appends it
    with a 12 digit lowercase alphanumeric string when it does not exist in the
    parameter store."""
    from dbt_copilot_helper.commands.conduit import get_or_create_task_name

    task_name = get_or_create_task_name(mock_application, "development", "app-postgres")
    random_id = task_name.rsplit("-", 1)[1]

    assert task_name.rsplit("-", 1)[0] == mock_task_name("app-postgres").rsplit("-", 1)[0]
    assert random_id.isalnum() and random_id.islower() and len(random_id) == 12


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("subprocess.call")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=True)
def test_connect_to_addon_client_task(
    addon_client_is_running, subprocess_call, addon_type, mock_application
):
    """
    Test that, given app, env, ECS cluster ARN and addon type,
    connect_to_addon_client_task calls addon_client_is_running with cluster ARN
    and addon type.

    It then subsequently calls subprocess.call with the correct app, env and
    addon type.
    """
    from dbt_copilot_helper.commands.conduit import addon_client_is_running
    from dbt_copilot_helper.commands.conduit import connect_to_addon_client_task

    task_name = mock_task_name(addon_type)
    connect_to_addon_client_task(mock_application, "development", "test-arn", task_name)

    addon_client_is_running.assert_called_once_with(
        mock_application, "development", "test-arn", task_name
    )
    subprocess_call.assert_called_once_with(
        f"copilot task exec --app test-application --env development "
        f"--name {task_name} "
        f"--command bash",
        shell=True,
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("time.sleep", return_value=None)
@patch("subprocess.call")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=False)
def test_connect_to_addon_client_task_when_timeout_reached(
    addon_client_is_running, subprocess_call, sleep, addon_type, mock_application
):
    """Test that, given app, env, ECS cluster ARN and addon type, when the
    client agent fails to start, connect_to_addon_client_task calls
    addon_client_is_running with cluster ARN and addon type 15 times, but does
    not call subprocess.call."""
    from dbt_copilot_helper.commands.conduit import CreateTaskTimeoutConduitError
    from dbt_copilot_helper.commands.conduit import connect_to_addon_client_task

    task_name = mock_task_name(addon_type)
    with pytest.raises(CreateTaskTimeoutConduitError):
        connect_to_addon_client_task(mock_application, "development", "test-arn", task_name)

    addon_client_is_running.assert_called_with(
        mock_application, "development", "test-arn", task_name
    )
    assert addon_client_is_running.call_count == 15
    subprocess_call.assert_not_called()


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.get_cluster_arn", return_value="test-arn")
@patch("dbt_copilot_helper.commands.conduit.get_or_create_task_name")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=False)
@patch("dbt_copilot_helper.commands.conduit.create_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.connect_to_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.add_stack_delete_policy_to_task_role")
@patch("dbt_copilot_helper.commands.conduit.update_conduit_stack_resources")
def test_start_conduit(
    update_conduit_stack_resources,
    add_stack_delete_policy_to_task_role,
    connect_to_addon_client_task,
    create_addon_client_task,
    addon_client_is_running,
    get_or_create_task_name,
    get_cluster_arn,
    addon_type,
    mock_application,
):
    """Test that given app, env and addon type strings, start_conduit calls
    get_cluster_arn, addon_client_is_running, created_addon_client_task,
    add_stack_delete_policy_to_task_role and connect_to_addon_client_task."""
    from dbt_copilot_helper.commands.conduit import start_conduit

    addon_name = addon_type.upper()
    task_name = mock_task_name(addon_name)
    get_or_create_task_name.side_effect = [task_name]

    start_conduit("test-application", "development", addon_type, addon_name)

    get_cluster_arn.assert_called_once_with(mock_application, "development")
    get_or_create_task_name.assert_called_once_with(mock_application, "development", addon_name)
    addon_client_is_running.assert_called_with(
        mock_application, "development", "test-arn", task_name
    )
    create_addon_client_task.assert_called_once_with(
        mock_application, "development", addon_type, addon_name, task_name
    )
    add_stack_delete_policy_to_task_role.assert_called_once_with(
        mock_application, "development", task_name
    )
    update_conduit_stack_resources.assert_called_once_with(
        mock_application, "development", addon_type, addon_name, task_name
    )
    connect_to_addon_client_task.assert_called_once_with(
        mock_application, "development", "test-arn", task_name
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.get_cluster_arn", return_value="test-arn")
@patch("dbt_copilot_helper.commands.conduit.get_or_create_task_name")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=False)
@patch("dbt_copilot_helper.commands.conduit.create_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.connect_to_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.add_stack_delete_policy_to_task_role")
@patch("dbt_copilot_helper.commands.conduit.update_conduit_stack_resources")
def test_start_conduit_with_custom_addon_name(
    update_conduit_stack_resources,
    add_stack_delete_policy_to_task_role,
    connect_to_addon_client_task,
    create_addon_client_task,
    addon_client_is_running,
    get_or_create_task_name,
    get_cluster_arn,
    addon_type,
    mock_application,
):
    """Test that given app, env, addon type and addon name strings,
    start_conduit calls get_cluster_arn, addon_client_is_running,
    created_addon_client_task, connect_to_addon_client_task and
    add_stack_delete_policy_to_task_role."""
    from dbt_copilot_helper.commands.conduit import start_conduit

    task_name = mock_task_name("custom-addon-name")
    get_or_create_task_name.side_effect = [task_name]

    start_conduit("test-application", "development", addon_type, "custom-addon-name")

    get_cluster_arn.assert_called_once_with(mock_application, "development")
    get_or_create_task_name.assert_called_once_with(
        mock_application, "development", "custom-addon-name"
    )
    addon_client_is_running.assert_called_with(
        mock_application, "development", "test-arn", task_name
    )
    create_addon_client_task.assert_called_once_with(
        mock_application, "development", addon_type, "custom-addon-name", task_name
    )
    add_stack_delete_policy_to_task_role.assert_called_once_with(
        mock_application, "development", task_name
    )
    update_conduit_stack_resources.assert_called_once_with(
        mock_application, "development", addon_type, "custom-addon-name", task_name
    )
    connect_to_addon_client_task.assert_called_once_with(
        mock_application, "development", "test-arn", task_name
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.get_cluster_arn")
@patch("dbt_copilot_helper.commands.conduit.get_or_create_task_name")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=False)
@patch("dbt_copilot_helper.commands.conduit.create_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.connect_to_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.add_stack_delete_policy_to_task_role")
@patch("dbt_copilot_helper.commands.conduit.update_conduit_stack_resources")
def test_start_conduit_when_no_cluster_present(
    update_conduit_stack_resources,
    add_stack_delete_policy_to_task_role,
    connect_to_addon_client_task,
    create_addon_client_task,
    addon_client_is_running,
    get_or_create_task_name,
    get_cluster_arn,
    addon_type,
    mock_application,
):
    """
    Test that given app, env, addon type and no available ecs cluster,
    start_conduit calls get_cluster_arn and the NoClusterConduitError is raised.

    Neither created_addon_client_task, addon_client_is_running,
    connect_to_addon_client_task or add_stack_delete_policy_to_task_role are
    called.
    """
    from dbt_copilot_helper.commands.conduit import NoClusterConduitError
    from dbt_copilot_helper.commands.conduit import start_conduit

    get_cluster_arn.side_effect = NoClusterConduitError

    with pytest.raises(NoClusterConduitError):
        start_conduit("test-application", "development", addon_type, "custom-addon-name")

    get_cluster_arn.assert_called_once_with(mock_application, "development")
    get_or_create_task_name.assert_not_called()
    addon_client_is_running.assert_not_called()
    create_addon_client_task.assert_not_called()
    add_stack_delete_policy_to_task_role.assert_not_called()
    update_conduit_stack_resources.assert_not_called()
    connect_to_addon_client_task.assert_not_called()


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.get_cluster_arn", return_value="test-arn")
@patch("dbt_copilot_helper.commands.conduit.get_or_create_task_name")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=False)
@patch("dbt_copilot_helper.commands.conduit.create_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.connect_to_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.add_stack_delete_policy_to_task_role")
@patch("dbt_copilot_helper.commands.conduit.update_conduit_stack_resources")
def test_start_conduit_when_no_secret_exists(
    update_conduit_stack_resources,
    add_stack_delete_policy_to_task_role,
    connect_to_addon_client_task,
    create_addon_client_task,
    addon_client_is_running,
    get_or_create_task_name,
    get_cluster_arn,
    addon_type,
    mock_application,
):
    """Test that given app, env, addon type and no available secret,
    start_conduit calls get_cluster_arn, then addon_client_is_running and
    create_addon_client_task and the NoConnectionSecretError is raised and
    add_stack_delete_policy_to_task_role and connect_to_addon_client_task are
    not called."""
    from dbt_copilot_helper.commands.conduit import SecretNotFoundConduitError
    from dbt_copilot_helper.commands.conduit import start_conduit

    addon_name = addon_type.upper()
    create_addon_client_task.side_effect = SecretNotFoundConduitError
    task_name = mock_task_name(addon_name)
    get_or_create_task_name.side_effect = [task_name]

    with pytest.raises(SecretNotFoundConduitError):
        start_conduit("test-application", "development", addon_type, addon_name)

    get_cluster_arn.assert_called_once_with(mock_application, "development")
    get_or_create_task_name.assert_called_once_with(mock_application, "development", addon_name)
    addon_client_is_running.assert_called_with(
        mock_application, "development", "test-arn", task_name
    )
    create_addon_client_task.assert_called_once_with(
        mock_application, "development", addon_type, addon_name, task_name
    )
    add_stack_delete_policy_to_task_role.assert_not_called()
    update_conduit_stack_resources.assert_not_called()
    connect_to_addon_client_task.assert_not_called()


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.get_cluster_arn", return_value="test-arn")
@patch("dbt_copilot_helper.commands.conduit.get_or_create_task_name")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=False)
@patch("dbt_copilot_helper.commands.conduit.create_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.connect_to_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.add_stack_delete_policy_to_task_role")
@patch("dbt_copilot_helper.commands.conduit.update_conduit_stack_resources")
def test_start_conduit_when_no_custom_addon_secret_exists(
    update_conduit_stack_resources,
    add_stack_delete_policy_to_task_role,
    connect_to_addon_client_task,
    create_addon_client_task,
    addon_client_is_running,
    get_or_create_task_name,
    get_cluster_arn,
    addon_type,
    mock_application,
):
    """Test that given app, env, addon type, addon name and no available custom
    addon secret, start_conduit calls get_cluster_arn, then
    addon_client_is_running, create_addon_client_task and the
    NoConnectionSecretError is raised and add_stack_delete_policy_to_task_role
    and connect_to_addon_client_task are not called."""
    from dbt_copilot_helper.commands.conduit import SecretNotFoundConduitError
    from dbt_copilot_helper.commands.conduit import start_conduit

    create_addon_client_task.side_effect = SecretNotFoundConduitError
    task_name = mock_task_name("custom-addon-name")
    get_or_create_task_name.side_effect = [task_name]

    with pytest.raises(SecretNotFoundConduitError):
        start_conduit("test-application", "development", addon_type, "custom-addon-name")

    get_cluster_arn.assert_called_once_with(mock_application, "development")
    get_or_create_task_name.assert_called_once_with(
        mock_application, "development", "custom-addon-name"
    )
    addon_client_is_running.assert_called_with(
        mock_application, "development", "test-arn", task_name
    )
    create_addon_client_task.assert_called_once_with(
        mock_application, "development", addon_type, "custom-addon-name", task_name
    )
    add_stack_delete_policy_to_task_role.assert_not_called()
    update_conduit_stack_resources.assert_not_called()
    connect_to_addon_client_task.assert_not_called()


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.get_cluster_arn", return_value="test-arn")
@patch("dbt_copilot_helper.commands.conduit.get_or_create_task_name")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=False)
@patch("dbt_copilot_helper.commands.conduit.create_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.connect_to_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.add_stack_delete_policy_to_task_role")
@patch("dbt_copilot_helper.commands.conduit.update_conduit_stack_resources")
def test_start_conduit_when_addon_client_task_fails_to_start(
    update_conduit_stack_resources,
    add_stack_delete_policy_to_task_role,
    connect_to_addon_client_task,
    create_addon_client_task,
    addon_client_is_running,
    get_or_create_task_name,
    get_cluster_arn,
    addon_type,
    mock_application,
):
    """Test that given app, env, and addon type strings when the client task
    fails to start, start_conduit calls get_cluster_arn,
    addon_client_is_running, create_addon_client_task,
    add_stack_delete_policy_to_task_role and connect_to_addon_client_task then
    the NoConnectionSecretError is raised."""
    from dbt_copilot_helper.commands.conduit import CreateTaskTimeoutConduitError
    from dbt_copilot_helper.commands.conduit import start_conduit

    addon_name = addon_type.upper()
    connect_to_addon_client_task.side_effect = CreateTaskTimeoutConduitError
    task_name = mock_task_name(addon_name)
    get_or_create_task_name.side_effect = [task_name]

    with pytest.raises(CreateTaskTimeoutConduitError):
        start_conduit("test-application", "development", addon_type, addon_name)

    get_cluster_arn.assert_called_once_with(mock_application, "development")
    get_or_create_task_name.assert_called_once_with(mock_application, "development", addon_name)
    addon_client_is_running.assert_called_with(
        mock_application, "development", "test-arn", task_name
    )
    create_addon_client_task.assert_called_once_with(
        mock_application, "development", addon_type, addon_name, task_name
    )
    add_stack_delete_policy_to_task_role.assert_called_once_with(
        mock_application, "development", task_name
    )
    update_conduit_stack_resources.assert_called_once_with(
        mock_application, "development", addon_type, addon_name, task_name
    )
    connect_to_addon_client_task.assert_called_once_with(
        mock_application, "development", "test-arn", task_name
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.get_cluster_arn", return_value="test-arn")
@patch("dbt_copilot_helper.commands.conduit.get_or_create_task_name")
@patch("dbt_copilot_helper.commands.conduit.create_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=True)
@patch("dbt_copilot_helper.commands.conduit.connect_to_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.add_stack_delete_policy_to_task_role")
@patch("dbt_copilot_helper.commands.conduit.update_conduit_stack_resources")
def test_start_conduit_when_addon_client_task_is_already_running(
    update_conduit_stack_resources,
    add_stack_delete_policy_to_task_role,
    connect_to_addon_client_task,
    addon_client_is_running,
    create_addon_client_task,
    get_or_create_task_name,
    get_cluster_arn,
    addon_type,
    mock_application,
):
    """Test that given app, env, and addon type strings when the client task is
    already running, start_conduit calls get_cluster_arn,
    addon_client_is_running and connect_to_addon_client_task then the
    create_addon_client_task and add_stack_delete_policy_to_task_role are not
    called."""
    from dbt_copilot_helper.commands.conduit import start_conduit

    addon_name = addon_type.upper()
    task_name = mock_task_name(addon_name)
    get_or_create_task_name.side_effect = [task_name]

    start_conduit("test-application", "development", addon_type, addon_name)

    get_cluster_arn.assert_called_once_with(mock_application, "development")
    get_or_create_task_name.assert_called_once_with(mock_application, "development", addon_name)
    addon_client_is_running.assert_called_once_with(
        mock_application, "development", "test-arn", task_name
    )
    create_addon_client_task.assert_not_called()
    add_stack_delete_policy_to_task_role.assert_not_called()
    update_conduit_stack_resources.assert_not_called()
    connect_to_addon_client_task.assert_called_once_with(
        mock_application, "development", "test-arn", task_name
    )


@pytest.mark.parametrize(
    "addon_type, addon_name",
    [
        ("postgres", "custom-name-postgres"),
        ("postgres", "custom-name-rds-postgres"),
        ("redis", "custom-name-redis"),
        ("opensearch", "custom-name-opensearch"),
    ],
)
@patch(
    "dbt_copilot_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_copilot_helper.commands.conduit.start_conduit")
def test_conduit_command(start_conduit, addon_type, addon_name, validate_version, fakefs):
    """Test that given an app, env and addon name strings, the conduit command
    calls start_conduit with app, env, addon type and addon name."""
    from dbt_copilot_helper.commands.conduit import conduit

    _create_test_manifest(fakefs)

    CliRunner().invoke(
        conduit,
        [
            "--app",
            "test-application",
            "--env",
            "development",
            "--addon-name",
            addon_name,
        ],
    )

    validate_version.assert_called_once()
    start_conduit.assert_called_once_with("test-application", "development", addon_type, addon_name)


@pytest.mark.parametrize(
    "addon_name",
    [
        "custom-name-postgres",
        "custom-name-rds-postgres",
        "custom-name-redis",
        "custom-name-opensearch",
    ],
)
@patch("click.secho")
@patch(
    "dbt_copilot_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_copilot_helper.commands.conduit.start_conduit")
def test_conduit_command_when_no_cluster_exists(
    start_conduit, secho, addon_name, validate_version, fakefs
):
    """Test that given an app, env and addon name strings, when there is no ECS
    Cluster available, the conduit command handles the NoClusterConduitError
    exception."""
    from dbt_copilot_helper.commands.conduit import NoClusterConduitError
    from dbt_copilot_helper.commands.conduit import conduit

    start_conduit.side_effect = NoClusterConduitError

    _create_test_manifest(fakefs)

    result = CliRunner().invoke(
        conduit,
        [
            "--app",
            "test-application",
            "--env",
            "development",
            "--addon-name",
            addon_name,
        ],
    )

    assert result.exit_code == 1
    validate_version.assert_called_once()
    secho.assert_called_once_with(
        """No ECS cluster found for "test-application" in "development" environment.""", fg="red"
    )


@pytest.mark.parametrize(
    "addon_name",
    [
        "custom-name-postgres",
        "custom-name-rds-postgres",
        "custom-name-redis",
        "custom-name-opensearch",
    ],
)
@patch("click.secho")
@patch(
    "dbt_copilot_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_copilot_helper.commands.conduit.start_conduit")
def test_conduit_command_when_no_connection_secret_exists(
    start_conduit, secho, addon_name, validate_version, fakefs
):
    """Test that given an app, env and addon name strings, when there is no
    connection secret available, the conduit command handles the
    NoConnectionSecretError exception."""
    from dbt_copilot_helper.commands.conduit import SecretNotFoundConduitError
    from dbt_copilot_helper.commands.conduit import conduit

    start_conduit.side_effect = SecretNotFoundConduitError(addon_name)

    _create_test_manifest(fakefs)

    result = CliRunner().invoke(
        conduit,
        [
            "--app",
            "test-application",
            "--env",
            "development",
            "--addon-name",
            addon_name,
        ],
    )

    assert result.exit_code == 1
    validate_version.assert_called_once()
    secho.assert_called_once_with(
        f"""No secret called "{addon_name.replace('-', '_').upper()}" for "test-application" in "development" environment.""",
        fg="red",
    )


@pytest.mark.parametrize(
    "addon_name",
    [
        "custom-name-postgres",
        "custom-name-rds-postgres",
        "custom-name-redis",
        "custom-name-opensearch",
    ],
)
@patch("click.secho")
@patch(
    "dbt_copilot_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_copilot_helper.commands.conduit.start_conduit")
def test_conduit_command_when_client_task_fails_to_start(
    start_conduit, secho, addon_name, validate_version, fakefs
):
    """Test that given an app, env and addon name strings, when the ECS client
    task fails to start, the conduit command handles the
    TaskConnectionTimeoutError exception."""
    from dbt_copilot_helper.commands.conduit import CreateTaskTimeoutConduitError
    from dbt_copilot_helper.commands.conduit import conduit

    start_conduit.side_effect = CreateTaskTimeoutConduitError

    _create_test_manifest(fakefs)

    result = CliRunner().invoke(
        conduit,
        [
            "--app",
            "test-application",
            "--env",
            "development",
            "--addon-name",
            addon_name,
        ],
    )

    assert result.exit_code == 1
    validate_version.assert_called_once()
    secho.assert_called_once_with(
        f"""Client ({addon_name}) ECS task has failed to start for "test-application" in "development" environment.""",
        fg="red",
    )


@patch("click.secho")
@patch(
    "dbt_copilot_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_copilot_helper.commands.conduit.start_conduit")
def test_conduit_command_when_addon_type_is_invalid(start_conduit, secho, validate_version, fakefs):
    """Test that given an app, env and addon name strings, if the addon type is
    invalid the conduit command handles the exception."""
    from dbt_copilot_helper.commands.conduit import conduit

    fakefs.create_file(
        "addons.yml",
        contents="""
    custom-name-postgres:
        type: nope
    """,
    )

    result = CliRunner().invoke(
        conduit,
        [
            "--app",
            "test-application",
            "--env",
            "development",
            "--addon-name",
            "custom-name-postgres",
        ],
    )

    assert result.exit_code == 1
    validate_version.assert_called_once()
    start_conduit.assert_not_called()
    secho.assert_called_once_with(
        """Addon type "nope" does not exist, try one of opensearch, rds-postgres, aurora-postgres, redis.""",
        fg="red",
    )


@patch("click.secho")
@patch(
    "dbt_copilot_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_copilot_helper.commands.conduit.start_conduit")
def test_conduit_command_when_addon_does_not_exist(start_conduit, secho, validate_version, fakefs):
    """Test that given an app, env and invalid addon name strings, the conduit
    command handles the exception."""
    from dbt_copilot_helper.commands.conduit import conduit

    fakefs.create_file(
        "addons.yml",
        contents="""
    custom-name-redis:
        type: redis
    """,
    )

    result = CliRunner().invoke(
        conduit,
        [
            "--app",
            "test-application",
            "--env",
            "development",
            "--addon-name",
            "custom-name-postgres",
        ],
    )

    assert result.exit_code == 1
    validate_version.assert_called_once()
    start_conduit.assert_not_called()
    secho.assert_called_once_with(
        """Addon "custom-name-postgres" does not exist.""",
        fg="red",
    )


def _create_test_manifest(fakefs):
    fakefs.create_file(
        "addons.yml",
        contents="""
    custom-name-postgres:
        type: aurora-postgres
    custom-name-rds-postgres:
        type: rds-postgres
    custom-name-opensearch:
        type: opensearch
    custom-name-redis:
        type: redis
    """,
    )
