from unittest.mock import patch

import boto3
import pytest
from click.testing import CliRunner
from moto import mock_ecs
from moto import mock_resourcegroupstaggingapi
from moto import mock_secretsmanager
from moto import mock_ssm

from dbt_copilot_helper.commands.conduit import CreateTaskTimeoutConduitError
from dbt_copilot_helper.commands.conduit import InvalidAddonTypeConduitError
from dbt_copilot_helper.commands.conduit import NoClusterConduitError
from dbt_copilot_helper.commands.conduit import SecretNotFoundConduitError
from dbt_copilot_helper.commands.conduit import addon_client_is_running
from dbt_copilot_helper.commands.conduit import conduit
from dbt_copilot_helper.commands.conduit import connect_to_addon_client_task
from dbt_copilot_helper.commands.conduit import create_addon_client_task
from dbt_copilot_helper.commands.conduit import get_cluster_arn
from dbt_copilot_helper.commands.conduit import get_connection_secret_arn
from dbt_copilot_helper.commands.conduit import normalise_string
from dbt_copilot_helper.commands.conduit import start_conduit


@pytest.mark.parametrize(
    "test_instance",
    [
        ("WORD", "word"),
        ("Some-String", "some-string"),
        ("SoMe_StriNg", "some-string"),
        ("Long String With Spaces", "long-string-with-spaces"),
    ],
)
def test_normalise_string(test_instance):
    """Test that given a set of strings, normalise_string produces the expected
    result."""
    assert normalise_string(test_instance[0]) == test_instance[1]


@mock_resourcegroupstaggingapi
def test_get_cluster_arn(mocked_cluster):
    """Test that, given app and environment strings, get_cluster_arn returns the
    arn of a cluster tagged with these strings."""

    assert (
        get_cluster_arn("test-application", "development")
        == mocked_cluster["cluster"]["clusterArn"]
    )


@mock_ecs
def test_get_cluster_arn_when_there_is_no_cluster():
    """Test that, given app and environment strings, get_cluster_arn raises an
    exception when no cluster tagged with these strings exists."""

    with pytest.raises(NoClusterConduitError):
        get_cluster_arn("test-application", "nope")


@mock_secretsmanager
def test_get_connection_secret_arn_from_secrets_manager():
    """Test that, given app, environment and secret name strings,
    get_connection_secret_arn returns an ARN from secrets manager."""
    mock_secretsmanager = boto3.client("secretsmanager")
    mock_secretsmanager.create_secret(
        Name="/copilot/test-application/development/secrets/POSTGRES",
        SecretString="something-secret",
    )

    arn = get_connection_secret_arn("test-application", "development", "POSTGRES")

    assert arn.startswith(
        "arn:aws:secretsmanager:eu-west-2:123456789012:secret:"
        "/copilot/test-application/development/secrets/POSTGRES-"
    )


@mock_secretsmanager
@mock_ssm
def test_get_connection_secret_arn_from_parameter_store():
    """Test that, given app, environment and secret name strings,
    get_connection_secret_arn returns an ARN from parameter store."""
    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name="/copilot/test-application/development/secrets/POSTGRES",
        Value="something-secret",
        Type="SecureString",
    )

    arn = get_connection_secret_arn("test-application", "development", "POSTGRES")

    assert (
        arn
        == "arn:aws:ssm:eu-west-2:123456789012:parameter/copilot/test-application/development/secrets/POSTGRES"
    )


@mock_secretsmanager
@mock_ssm
def test_get_connection_secret_arn_when_secret_does_not_exist():
    """Test that, given app, environment and secret name strings,
    get_connection_secret_arn raises an exception when no matching secret exists
    in secrets manager or parameter store."""
    with pytest.raises(SecretNotFoundConduitError):
        get_connection_secret_arn("test-application", "development", "POSTGRES")


@patch("subprocess.call")
@patch("dbt_copilot_helper.commands.conduit.get_connection_secret_arn", return_value="test-arn")
def test_create_addon_client_task(get_connection_secret_arn, subprocess_call):
    """Test that, given app and environment strings, create_addon_client_task
    calls get_connection_secret_arn with the default secret name and
    subsequently subprocess.call with the correct secret ARN."""
    create_addon_client_task("test-application", "development", "postgres", "postgres")

    get_connection_secret_arn.assert_called_once_with("test-application", "development", "POSTGRES")
    subprocess_call.assert_called_once_with(
        "copilot task run --app test-application --env development "
        "--task-group-name conduit-test-application-development-postgres "
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
def test_create_addon_client_task_with_addon_name(get_connection_secret_arn, subprocess_call):
    """Test that, given app, environment and secret name strings,
    create_addon_client_task calls get_connection_secret_arn with the custom
    secret name and subsequently subprocess.call with the correct secret ARN."""
    create_addon_client_task("test-application", "development", "postgres", "named_postgres")

    get_connection_secret_arn.assert_called_once_with(
        "test-application", "development", "NAMED_POSTGRES"
    )
    subprocess_call.assert_called_once_with(
        "copilot task run --app test-application --env development "
        "--task-group-name conduit-test-application-development-named-postgres "
        "--image public.ecr.aws/uktrade/tunnel:postgres "
        "--secrets CONNECTION_SECRET=test-named-arn "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


@patch("subprocess.call")
@patch(
    "dbt_copilot_helper.commands.conduit.get_connection_secret_arn",
    side_effect=SecretNotFoundConduitError,
)
def test_create_addon_client_task_when_no_secret_found(get_connection_secret_arn, subprocess_call):
    """Test that, given app, environment and secret name strings,
    create_addon_client_task raises a NoConnectionSecretError and does not call
    subprocess.call."""
    with pytest.raises(SecretNotFoundConduitError):
        create_addon_client_task("test-application", "development", "postgres", "named-postgres")

        subprocess_call.assert_not_called()


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_addon_client_is_running(mock_cluster_client_task, mocked_cluster, addon_type):
    """Test that, given cluster ARN, addon type and with a running agent,
    addon_client_is_running returns True."""
    mocked_cluster_for_client = mock_cluster_client_task(addon_type)
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]

    with patch(
        "dbt_copilot_helper.commands.conduit.boto3.client", return_value=mocked_cluster_for_client
    ):
        assert addon_client_is_running(
            "test-application", "development", mocked_cluster_arn, addon_type
        )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_addon_client_is_running_when_no_client_task_running(
    mock_cluster_client_task, mocked_cluster, addon_type
):
    """Test that, given cluster ARN, addon type and without a running client
    task, addon_client_is_running returns False."""
    mocked_cluster_for_client = mock_cluster_client_task(addon_type, task_running=False)
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]

    with patch(
        "dbt_copilot_helper.commands.conduit.boto3.client", return_value=mocked_cluster_for_client
    ):
        assert (
            addon_client_is_running(
                "test-application", "development", mocked_cluster_arn, addon_type
            )
            is False
        )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_addon_client_is_running_when_no_client_agent_running(
    mock_cluster_client_task, mocked_cluster, addon_type
):
    """Test that, given cluster ARN, addon type and without a running agent,
    addon_client_is_running returns False."""
    mocked_cluster_for_client = mock_cluster_client_task(addon_type, "ACTIVATING")
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]

    with patch(
        "dbt_copilot_helper.commands.conduit.boto3.client", return_value=mocked_cluster_for_client
    ):
        assert (
            addon_client_is_running(
                "test-application", "development", mocked_cluster_arn, addon_type
            )
            is False
        )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("subprocess.call")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=True)
def test_connect_to_addon_client_task(addon_client_is_running, subprocess_call, addon_type):
    """
    Test that, given app, env, ECS cluster ARN and addon type,
    connect_to_addon_client_task calls addon_client_is_running with cluster ARN
    and addon type.

    It then subsequently calls subprocess.call with the correct app, env and
    addon type.
    """
    connect_to_addon_client_task("test-application", "development", "test-arn", addon_type)

    addon_client_is_running.assert_called_once_with(
        "test-application", "development", "test-arn", addon_type
    )
    subprocess_call.assert_called_once_with(
        f"copilot task exec --app test-application --env development "
        f"--name conduit-test-application-development-{addon_type} "
        f"--command bash",
        shell=True,
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("time.sleep")
@patch("subprocess.call")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=False)
def test_connect_to_addon_client_task_when_timeout_reached(
    addon_client_is_running, subprocess_call, sleep, addon_type
):
    """Test that, given app, env, ECS cluster ARN and addon type, when the
    client agent fails to start, connect_to_addon_client_task calls
    addon_client_is_running with cluster ARN and addon type 15 times, but does
    not call subprocess.call."""
    with pytest.raises(CreateTaskTimeoutConduitError):
        connect_to_addon_client_task("test-application", "development", "test-arn", addon_type)

    addon_client_is_running.assert_called_with(
        "test-application", "development", "test-arn", addon_type
    )
    assert addon_client_is_running.call_count == 15
    subprocess_call.assert_not_called()


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.get_cluster_arn", return_value="test-arn")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=False)
@patch("dbt_copilot_helper.commands.conduit.create_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.connect_to_addon_client_task")
def test_start_conduit(
    connect_to_addon_client_task,
    create_addon_client_task,
    addon_client_is_running,
    get_cluster_arn,
    addon_type,
):
    """Test that given app, env and addon type strings, start_conduit calls
    get_cluster_arn, addon_client_is_running, created_addon_client_task and
    connect_to_addon_client_task."""
    start_conduit("test-application", "development", addon_type, None)

    get_cluster_arn.assert_called_once_with("test-application", "development")
    addon_client_is_running.assert_called_with(
        "test-application", "development", "test-arn", addon_type
    )
    create_addon_client_task.assert_called_once_with(
        "test-application", "development", addon_type, addon_type
    )
    connect_to_addon_client_task.assert_called_once_with(
        "test-application", "development", "test-arn", addon_type
    )


@patch(
    "dbt_copilot_helper.commands.conduit.get_cluster_arn",
)
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running")
@patch("dbt_copilot_helper.commands.conduit.create_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.connect_to_addon_client_task")
def test_start_conduit_when_addon_type_is_invalid(
    connect_to_addon_client_task, create_addon_client_task, addon_client_is_running, get_cluster_arn
):
    """
    Test that given app, env and invalid addon type, start_conduit raises an
    InvalidAddonTypeConduitError.

    Neither get_cluster_arn, created_addon_client_task, addon_client_is_running
    or connect_to_addon_client_task are called.
    """
    with pytest.raises(InvalidAddonTypeConduitError):
        start_conduit("test-application", "development", "nope")

    get_cluster_arn.assert_not_called()
    addon_client_is_running.assert_not_called()
    create_addon_client_task.assert_not_called()
    connect_to_addon_client_task.assert_not_called()


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.get_cluster_arn", return_value="test-arn")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=False)
@patch("dbt_copilot_helper.commands.conduit.create_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.connect_to_addon_client_task")
def test_start_conduit_with_custom_addon_name(
    connect_to_addon_client_task,
    create_addon_client_task,
    addon_client_is_running,
    get_cluster_arn,
    addon_type,
):
    """Test that given app, env, addon type and addon name strings,
    start_conduit calls get_cluster_arn, addon_client_is_running,
    created_addon_client_task and connect_to_addon_client_task."""
    start_conduit("test-application", "development", addon_type, "custom-addon-name")

    get_cluster_arn.assert_called_once_with("test-application", "development")
    addon_client_is_running.assert_called_with(
        "test-application", "development", "test-arn", "custom-addon-name"
    )
    create_addon_client_task.assert_called_once_with(
        "test-application", "development", addon_type, "custom-addon-name"
    )
    connect_to_addon_client_task.assert_called_once_with(
        "test-application", "development", "test-arn", "custom-addon-name"
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.get_cluster_arn", side_effect=NoClusterConduitError)
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=False)
@patch("dbt_copilot_helper.commands.conduit.create_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.connect_to_addon_client_task")
def test_start_conduit_when_no_cluster_present(
    connect_to_addon_client_task,
    create_addon_client_task,
    addon_client_is_running,
    get_cluster_arn,
    addon_type,
):
    """
    Test that given app, env, addon type and no available ecs cluster,
    start_conduit calls get_cluster_arn and the NoClusterConduitError is raised.

    Neither created_addon_client_task, addon_client_is_running or
    connect_to_addon_client_task are called.
    """
    with pytest.raises(NoClusterConduitError):
        start_conduit("test-application", "development", addon_type, "custom-addon-name")

    get_cluster_arn.assert_called_once_with("test-application", "development")
    addon_client_is_running.assert_not_called()
    create_addon_client_task.assert_not_called()
    connect_to_addon_client_task.assert_not_called()


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.get_cluster_arn", return_value="test-arn")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=False)
@patch(
    "dbt_copilot_helper.commands.conduit.create_addon_client_task",
    side_effect=SecretNotFoundConduitError,
)
@patch("dbt_copilot_helper.commands.conduit.connect_to_addon_client_task")
def test_start_conduit_when_no_secret_exists(
    connect_to_addon_client_task,
    create_addon_client_task,
    addon_client_is_running,
    get_cluster_arn,
    addon_type,
):
    """Test that given app, env, addon type and no available secret,
    start_conduit calls get_cluster_arn, then addon_client_is_running and
    create_addon_client_task and the NoConnectionSecretError is raised and
    connect_to_addon_client_task is not called."""
    with pytest.raises(SecretNotFoundConduitError):
        start_conduit("test-application", "development", addon_type)

    get_cluster_arn.assert_called_once_with("test-application", "development")
    addon_client_is_running.assert_called_with(
        "test-application", "development", "test-arn", addon_type
    )
    create_addon_client_task.assert_called_once_with(
        "test-application", "development", addon_type, addon_type
    )
    connect_to_addon_client_task.assert_not_called()


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.get_cluster_arn", return_value="test-arn")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=False)
@patch(
    "dbt_copilot_helper.commands.conduit.create_addon_client_task",
    side_effect=SecretNotFoundConduitError,
)
@patch("dbt_copilot_helper.commands.conduit.connect_to_addon_client_task")
def test_start_conduit_when_no_custom_addon_secret_exists(
    connect_to_addon_client_task,
    create_addon_client_task,
    addon_client_is_running,
    get_cluster_arn,
    addon_type,
):
    """Test that given app, env, addon type, addon name and no available custom
    addon secret, start_conduit calls get_cluster_arn, then
    addon_client_is_running, create_addon_client_task and the
    NoConnectionSecretError is raised and connect_to_addon_client_task is not
    called."""
    with pytest.raises(SecretNotFoundConduitError):
        start_conduit("test-application", "development", addon_type, "custom-addon-name")

    get_cluster_arn.assert_called_once_with("test-application", "development")
    addon_client_is_running.assert_called_with(
        "test-application", "development", "test-arn", "custom-addon-name"
    )
    create_addon_client_task.assert_called_once_with(
        "test-application", "development", addon_type, "custom-addon-name"
    )
    connect_to_addon_client_task.assert_not_called()


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.get_cluster_arn", return_value="test-arn")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=False)
@patch("dbt_copilot_helper.commands.conduit.create_addon_client_task")
@patch(
    "dbt_copilot_helper.commands.conduit.connect_to_addon_client_task",
    side_effect=CreateTaskTimeoutConduitError,
)
def test_start_conduit_when_addon_client_task_fails_to_start(
    connect_to_addon_client_task,
    create_addon_client_task,
    addon_client_is_running,
    get_cluster_arn,
    addon_type,
):
    """Test that given app, env, and addon type strings when the client task
    fails to start, start_conduit calls get_cluster_arn,
    addon_client_is_running, create_addon_client_task and
    connect_to_addon_client_task then the NoConnectionSecretError is raised."""
    with pytest.raises(CreateTaskTimeoutConduitError):
        start_conduit("test-application", "development", addon_type)

    get_cluster_arn.assert_called_once_with("test-application", "development")
    addon_client_is_running.assert_called_with(
        "test-application", "development", "test-arn", addon_type
    )
    create_addon_client_task.assert_called_once_with(
        "test-application", "development", addon_type, addon_type
    )
    connect_to_addon_client_task.assert_called_once_with(
        "test-application", "development", "test-arn", addon_type
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.get_cluster_arn", return_value="test-arn")
@patch("dbt_copilot_helper.commands.conduit.create_addon_client_task")
@patch("dbt_copilot_helper.commands.conduit.addon_client_is_running", return_value=True)
@patch("dbt_copilot_helper.commands.conduit.connect_to_addon_client_task")
def test_start_conduit_when_addon_client_task_is_already_running(
    connect_to_addon_client_task,
    addon_client_is_running,
    create_addon_client_task,
    get_cluster_arn,
    addon_type,
):
    """Test that given app, env, and addon type strings when the client task is
    already running, start_conduit calls get_cluster_arn,
    addon_client_is_running and connect_to_addon_client_task then the
    create_addon_client_task is not called."""
    start_conduit("test-application", "development", addon_type)

    get_cluster_arn.assert_called_once_with("test-application", "development")
    addon_client_is_running.assert_called_once_with(
        "test-application", "development", "test-arn", addon_type
    )
    create_addon_client_task.assert_not_called()
    connect_to_addon_client_task.assert_called_once_with(
        "test-application", "development", "test-arn", addon_type
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.start_conduit")
def test_conduit_command(start_conduit, addon_type):
    """Test that given an addon type, app and env strings, the conduit command
    calls start_conduit with app, env, addon type and no addon name."""
    CliRunner().invoke(
        conduit,
        [
            addon_type,
            "--app",
            "test-application",
            "--env",
            "development",
        ],
    )

    start_conduit.assert_called_once_with("test-application", "development", addon_type, None)


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("dbt_copilot_helper.commands.conduit.start_conduit")
def test_conduit_command_with_addon_name(start_conduit, addon_type):
    """Test that given an addon type, app, env and addon name strings, the
    conduit command calls start_conduit with app, env, addon type and custom
    addon name."""
    CliRunner().invoke(
        conduit,
        [
            addon_type,
            "--app",
            "test-application",
            "--env",
            "development",
            "--addon-name",
            "custom-addon",
        ],
    )

    start_conduit.assert_called_once_with(
        "test-application", "development", addon_type, "custom-addon"
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("click.secho")
@patch("dbt_copilot_helper.commands.conduit.start_conduit", side_effect=NoClusterConduitError)
def test_conduit_command_when_no_cluster_exists(start_conduit, secho, addon_type):
    """Test that given an addon type, app and env strings, when there is no ECS
    Cluster available, the conduit command handles the NoClusterConduitError
    exception."""
    result = CliRunner().invoke(
        conduit,
        [
            addon_type,
            "--app",
            "test-application",
            "--env",
            "development",
        ],
    )

    assert result.exit_code == 1
    secho.assert_called_once_with(
        """No ECS cluster found for "test-application" in "development" environment.""", fg="red"
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("click.secho")
@patch("dbt_copilot_helper.commands.conduit.start_conduit")
def test_conduit_command_when_no_connection_secret_exists(start_conduit, secho, addon_type):
    """Test that given an addon type, app and env strings, when there is no
    connection secret available, the conduit command handles the
    NoConnectionSecretError exception."""
    start_conduit.side_effect = SecretNotFoundConduitError(addon_type)

    result = CliRunner().invoke(
        conduit,
        [
            addon_type,
            "--app",
            "test-application",
            "--env",
            "development",
        ],
    )

    assert result.exit_code == 1
    secho.assert_called_once_with(
        f"""No secret called "{addon_type}" for "test-application" in "development" environment.""",
        fg="red",
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("click.secho")
@patch("dbt_copilot_helper.commands.conduit.start_conduit")
def test_conduit_command_when_no_connection_secret_exists_with_addon_name(
    start_conduit, secho, addon_type
):
    """Test that given an addon type, app, env and addon name strings, when
    there is no connection secret available, the conduit command handles the
    NoConnectionSecretError exception with addon name."""
    start_conduit.side_effect = SecretNotFoundConduitError(addon_type)

    result = CliRunner().invoke(
        conduit,
        [
            addon_type,
            "--app",
            "test-application",
            "--env",
            "development",
            "--addon-name",
            "custom-addon",
        ],
    )

    assert result.exit_code == 1
    secho.assert_called_once_with(
        """No secret called "custom-addon" for "test-application" in "development" environment.""",
        fg="red",
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
@patch("click.secho")
@patch(
    "dbt_copilot_helper.commands.conduit.start_conduit", side_effect=CreateTaskTimeoutConduitError
)
def test_conduit_command_when_client_task_fails_to_start(start_conduit, secho, addon_type):
    """Test that given an addon type, app and env strings, when the ECS client
    task fails to start, the conduit command handles the
    TaskConnectionTimeoutError exception."""
    result = CliRunner().invoke(
        conduit,
        [
            addon_type,
            "--app",
            "test-application",
            "--env",
            "development",
        ],
    )

    assert result.exit_code == 1
    secho.assert_called_once_with(
        f"""Client ({addon_type}) ECS task has failed to start for "test-application" in "development" environment.""",
        fg="red",
    )


@patch("click.secho")
@patch(
    "dbt_copilot_helper.commands.conduit.start_conduit", side_effect=InvalidAddonTypeConduitError
)
def test_conduit_command_when_addon_type_is_invalid(start_conduit, secho):
    """Test that given an invalid addon type, app and env strings, the conduit
    command handles the InvalidAddonTypeConduitError exception."""
    result = CliRunner().invoke(
        conduit,
        [
            "nope",
            "--app",
            "test-application",
            "--env",
            "development",
        ],
    )

    assert result.exit_code == 2
    assert (
        "Invalid value for '{opensearch|postgres|redis}': 'nope' is not one of 'opensearch', "
        "'postgres', 'redis'"
    ) in result.output
