import json
from unittest.mock import patch

import boto3
import pytest
from click.testing import CliRunner
from freezegun import freeze_time
from moto import mock_ec2
from moto import mock_ecs
from moto import mock_resourcegroupstaggingapi
from moto import mock_secretsmanager
from moto import mock_sts
from moto.ec2 import utils as ec2_utils

from commands.conduit_cli import create_task
from commands.conduit_cli import exec_into_task
from commands.conduit_cli import get_addon_command
from commands.conduit_cli import get_cluster_arn
from commands.conduit_cli import get_postgres_secret
from commands.conduit_cli import get_redis_cluster
from commands.conduit_cli import is_task_running
from commands.conduit_cli import tunnel
from commands.conduit_cli import update_postgres_command


@mock_resourcegroupstaggingapi
def test_get_cluster_arn(alias_session, mocked_cluster):
    """Test that, given app and environment strings, get_cluster_arn returns the
    arn of a cluster tagged with these strings."""

    expected_arn = mocked_cluster["cluster"]["clusterArn"]

    assert get_cluster_arn("dbt-app", "staging") == expected_arn


@pytest.mark.parametrize("addon_type", ["postgres", "redis"])
@patch("subprocess.call")
def test_create_task(subprocess_call, mocked_pg_secret, addon_type):
    """Test that create_task runs the `copilot task run` command with expected
    --app and --env flags."""

    create_task("dbt-app", "staging", addon_type, "POSTGRES")
    command = f"copilot task run -n tunnel-{addon_type} --image public.ecr.aws/uktrade/tunnel-{addon_type} --app dbt-app --env staging"
    if addon_type == "postgres":
        expected_arn = mocked_pg_secret["ARN"]
        command += f" --secrets DB_SECRET={expected_arn} --env-vars POSTGRES_PASSWORD=abc123"

    subprocess_call.assert_called_once_with(
        command,
        shell=True,
    )


def test_get_postgres_secret(mocked_pg_secret):
    """Test that, given app and environment strings, get_postgres_secret returns
    the app's secret arn string."""

    expected_arn = mocked_pg_secret["ARN"]
    secret_response = get_postgres_secret("dbt-app", "staging", "POSTGRES")

    assert secret_response["ARN"] == expected_arn
    assert (
        secret_response["SecretString"]
        == '{"password":"abc123","dbname":"main","engine":"postgres","port":5432,"dbInstanceIdentifier":"dbt-app-staging-addons-postgresdbinstance-blah","host":"dbt-app-staging-addons-postgresdbinstance-blah.whatever.eu-west-2.rds.amazonaws.com","username":"postgres"}'
    )
    assert secret_response["Name"] == "/copilot/dbt-app/staging/secrets/POSTGRES"


@mock_secretsmanager
def test_get_postgres_secret_with_custom_name():
    """Test that, given app, environment, and name strings, get_postgres_secret
    returns the app's custom named Postgres credentials from Secrets Manager."""
    mocked_secretsmanager = boto3.client("secretsmanager")

    secret_resource = {
        "Name": "/copilot/dbt-app/staging/secrets/custom-name",
        "Description": "A test parameter",
        "SecretString": '{"password":"abc123","dbname":"main","engine":"postgres","port":5432,"dbInstanceIdentifier":"dbt-app-staging-addons-postgresdbinstance-blah","host":"dbt-app-staging-addons-postgresdbinstance-blah.whatever.eu-west-2.rds.amazonaws.com","username":"postgres"}',
    }

    mocked_secretsmanager.create_secret(**secret_resource)

    secret_response = get_postgres_secret("dbt-app", "staging", "custom-name")

    assert secret_response["SecretString"] == secret_resource["SecretString"]
    assert secret_response["Name"] == secret_resource["Name"]


def test_is_task_running_when_task_is_not_running(mocked_cluster):
    """Given an ECS Cluster ARN string, is_task_running should return False when
    the task is not running."""

    assert not is_task_running(mocked_cluster["cluster"]["clusterArn"], "postgres")


@pytest.mark.parametrize("addon_type", ["postgres", "redis"])
@mock_ec2
def test_is_task_running(mocked_cluster, addon_type):
    """Given an ECS Cluster ARN string, is_task_running should return True when
    the task is running."""

    # Create mocked ECS Cluster
    mocked_ecs_client = boto3.client("ecs")
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    # Create mocked EC2 instance
    mocked_ec2_client = boto3.client("ec2")
    mocked_ec2_images = mocked_ec2_client.describe_images(Owners=["amazon"])["Images"]
    mocked_ec2_client.run_instances(ImageId=mocked_ec2_images[0]["ImageId"], MinCount=1, MaxCount=1)
    mocked_ec2_instances = boto3.client("ec2").describe_instances()
    mocked_ec2_instance_id = mocked_ec2_instances["Reservations"][0]["Instances"][0]["InstanceId"]
    mocked_ec2 = boto3.resource("ec2")
    mocked_ec2_instance = mocked_ec2.Instance(mocked_ec2_instance_id)
    mocked_instance_id_document = json.dumps(ec2_utils.generate_instance_identity_document(mocked_ec2_instance))
    # Attach mocked EC2 instance to the mocked ECS Cluster
    mocked_ecs_client.register_container_instance(
        cluster=mocked_cluster_arn, instanceIdentityDocument=mocked_instance_id_document
    )
    mocked_task_definition_arn = mocked_ecs_client.register_task_definition(
        family=f"copilot-tunnel-{addon_type}",
        containerDefinitions=[
            {"name": "test_container", "image": "test_image", "cpu": 100, "memory": 500, "essential": True}
        ],
    )["taskDefinition"]["taskDefinitionArn"]
    mocked_ecs_client.run_task(
        cluster=mocked_cluster_arn, taskDefinition=mocked_task_definition_arn, enableExecuteCommand=True
    )

    # moto does not yet provide the ability to mock an executable task and its managed agents / containers, so we need to patch the expected response
    def describe_tasks(cluster, tasks):
        return {
            "tasks": [
                {
                    "lastStatus": "RUNNING",
                    "containers": [{"managedAgents": [{"name": "ExecuteCommandAgent", "lastStatus": "RUNNING"}]}],
                }
            ]
        }

    mocked_ecs_client.describe_tasks = describe_tasks

    with patch("commands.conduit_cli.boto3.client", return_value=mocked_ecs_client):
        assert is_task_running(mocked_cluster_arn, addon_type)


@pytest.mark.parametrize("addon_type", ["postgres", "redis"])
@patch("os.system")
@patch("commands.conduit_cli.get_addon_command", return_value="test command")
@patch("commands.conduit_cli.is_task_running", return_value=True)
def test_exec_into_task(is_task_running, get_addon_command, system, addon_type):
    """Test that exec_into_task runs the `copilot task exec` command with
    expected --app and --env flags."""

    exec_into_task("dbt-app", "staging", "arn:random", addon_type)

    get_addon_command.assert_called_once_with("dbt-app", "staging", addon_type, "POSTGRES")
    system.assert_called_once_with("copilot task exec --app dbt-app --env staging --command 'test command'")


@freeze_time("Jan 14th, 2020", auto_tick_seconds=60)
def test_exec_into_task_timeout(capsys):
    exec_into_task("dbt-app", "staging", "arn:random", "postgres")

    assert (
        capsys.readouterr().out
        == "Attempt to exec into running task timed out. Try again by running `copilot task exec --app dbt-app --env staging` or check status of task in Amazon ECS console.\n"
    )


@mock_ecs
@mock_resourcegroupstaggingapi
@mock_sts
def test_tunnel_no_cluster_resource(alias_session):
    """Test that tunnel command prints an exit code when a cluster with app and
    env tags is not found."""

    result = CliRunner().invoke(tunnel, ["--project-profile", "foo", "--app", "dbt-app", "--env", "staging"])

    assert result.exit_code == 0
    assert "No cluster resource found with tag filter values dbt-app and staging" in result.output


@mock_sts
def test_tunnel_profile_not_configured():
    """Test that tunnel calls check_aws_conn and outputs expected error when AWS
    profile isn't configured."""

    result = CliRunner().invoke(tunnel, ["--project-profile", "foo", "--app", "dbt-app", "--env", "staging"])

    assert 'AWS profile "foo" is not configured.' in result.output


@pytest.mark.parametrize("addon_type", ["postgres", "redis"])
@mock_resourcegroupstaggingapi
@mock_sts
@patch("commands.conduit_cli.exec_into_task")
@patch("commands.conduit_cli.create_task")
def test_tunnel_task_not_running(
    create_task, exec_into_task, alias_session, mocked_cluster, mocked_pg_secret, addon_type
):
    """Test that, when a task is not already running, command creates and execs
    into a task."""

    cluster_arn = mocked_cluster["cluster"]["clusterArn"]

    CliRunner().invoke(
        tunnel, ["--project-profile", "foo", "--app", "dbt-app", "--env", "staging", "--addon-type", addon_type]
    )

    create_task.assert_called_once_with("dbt-app", "staging", addon_type, "POSTGRES")
    exec_into_task.assert_called_once_with("dbt-app", "staging", cluster_arn, addon_type)


@pytest.mark.parametrize("addon_type", ["postgres", "redis"])
# patching is_task_running because it's tested separately above and requires a lot of moto legwork.
@mock_resourcegroupstaggingapi
@mock_secretsmanager
@mock_sts
@patch("commands.conduit_cli.is_task_running", return_value=True)
@patch("commands.conduit_cli.exec_into_task")
@patch("commands.conduit_cli.create_task")
def test_tunnel_task_already_running(
    create_task, exec_into_task, is_task_running, alias_session, mocked_cluster, addon_type
):
    """Test that, when a task is already running, command execs into this task
    and does not create a new one."""

    cluster_arn = mocked_cluster["cluster"]["clusterArn"]

    CliRunner().invoke(
        tunnel, ["--project-profile", "foo", "--app", "dbt-app", "--env", "staging", "--addon-type", addon_type]
    )

    assert not create_task.called
    exec_into_task.assert_called_once_with("dbt-app", "staging", cluster_arn, addon_type)


@mock_resourcegroupstaggingapi
@mock_sts
@patch("commands.conduit_cli.exec_into_task")
@patch("commands.conduit_cli.create_task")
def test_tunnel_task_with_custom_db_secret_name(
    create_task, exec_into_task, alias_session, mocked_cluster, mocked_pg_secret
):
    """Test that, when a task is not already running, command creates and execs
    into a task with optional --db-secret-name flag."""

    cluster_arn = mocked_cluster["cluster"]["clusterArn"]

    CliRunner().invoke(
        tunnel,
        [
            "--project-profile",
            "foo",
            "--app",
            "dbt-app",
            "--env",
            "staging",
            "--db-secret-name",
            "custom-db-secret-name",
        ],
    )

    create_task.assert_called_once_with("dbt-app", "staging", "postgres", "custom-db-secret-name")
    exec_into_task.assert_called_once_with("dbt-app", "staging", cluster_arn, "postgres")


@mock_resourcegroupstaggingapi
@mock_secretsmanager
@mock_sts
@patch("commands.conduit_cli.is_task_running", return_value=False)
def test_tunnel_secret_not_found(is_task_running, alias_session, mocked_cluster):
    result = CliRunner().invoke(tunnel, ["--project-profile", "foo", "--app", "dbt-app", "--env", "staging"])

    assert "No secret found matching application dbt-app and environment staging." in result.output


def test_update_postgres_command(mocked_pg_secret):
    command = "copilot task run -n tunnel-postgres --image test-location.ecr --app dbt-app --env staging"
    updated_command = update_postgres_command("dbt-app", "staging", command, "POSTGRES")

    assert (
        updated_command
        == f"copilot task run -n tunnel-postgres --image test-location.ecr --app dbt-app --env staging --secrets DB_SECRET={mocked_pg_secret['ARN']} --env-vars POSTGRES_PASSWORD=abc123"
    )


# moto doesn't support creating cache clusters so we have to mock the api output ourselves
@patch(
    "commands.conduit_cli.botocore.client.BaseClient._make_api_call",
    side_effect=[
        {"CacheClusters": [{"ARN": "arn:dummy-arn"}]},
        {
            "ResourceTagMappingList": [
                {
                    "Tags": [
                        {"Key": "copilot-application", "Value": "dbt-app"},
                        {"Key": "copilot-environment", "Value": "staging"},
                    ]
                }
            ]
        },
    ],
)
def test_get_redis_cluster(make_api_call):
    cluster = get_redis_cluster("dbt-app", "staging")

    assert cluster == {"ARN": "arn:dummy-arn"}


def test_get_addon_command_postgres(mocked_pg_secret):
    expected_command = "psql postgres://postgres:abc123@dbt-app-staging-addons-postgresdbinstance-blah.whatever.eu-west-2.rds.amazonaws.com:5432/main"

    assert get_addon_command("dbt-app", "staging", "postgres", "POSTGRES") == expected_command


@patch(
    "commands.conduit_cli.get_redis_cluster",
    return_value={"CacheNodes": [{"Endpoint": {"Address": "test.redis.endpoint", "Port": 6379}}]},
)
def test_get_addon_command_redis(get_redis_cluster_mock):
    expected_command = "redis-cli -c -h test.redis.endpoint --tls -p 6379"

    assert get_addon_command("dbt-app", "staging", "redis") == expected_command
    get_redis_cluster_mock.assert_called_once_with("dbt-app", "staging")
