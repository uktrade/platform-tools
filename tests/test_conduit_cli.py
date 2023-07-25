import json
from unittest.mock import patch

import boto3
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
from commands.conduit_cli import get_cluster_arn
from commands.conduit_cli import get_postgres_secret_arn
from commands.conduit_cli import is_task_running
from commands.conduit_cli import tunnel


@mock_ecs
@mock_resourcegroupstaggingapi
def test_get_cluster_arn(alias_session):
    """Test that, given app and environment strings, get_cluster_arn returns the
    arn of a cluster tagged with these strings."""

    arn = boto3.client("ecs").create_cluster(
        tags=[
            {"key": "copilot-application", "value": "dbt-app"},
            {"key": "copilot-environment", "value": "staging"},
            {"key": "aws:cloudformation:logical-id", "value": "Cluster"},
        ]
    )["cluster"]["clusterArn"]

    assert get_cluster_arn("dbt-app", "staging") == arn


@patch("subprocess.call")
def test_create_task(subprocess_call):
    """Test that create_task runs the `copilot task run` command with expected
    --app and --env flags."""

    create_task("dbt-app", "staging", "arn::blah")

    subprocess_call.assert_called_once_with(
        "copilot task run -n dbtunnel --dockerfile Dockerfile --secrets DB_SECRET=arn::blah --app dbt-app --env staging",
        shell=True,
    )


@mock_secretsmanager
def test_get_postgres_secret_arn():
    """Test that, given app and environment strings, get_postgres_secret_arn
    returns the app's secret arn string."""

    arn = boto3.client("secretsmanager").create_secret(
        Name="/copilot/dbt-app/staging/secrets/POSTGRES", SecretString="secretivestring"
    )["ARN"]

    assert get_postgres_secret_arn("dbt-app", "staging") == arn


@mock_ec2
@mock_ecs
def test_is_task_running():
    """Test that, given a cluster arn string, is_task_running returns False
    until an ecs task is running on an ec2 instance in that cluster."""

    ecs_client = boto3.client("ecs")
    arn = ecs_client.create_cluster(
        tags=[
            {"key": "copilot-application", "value": "dbt-app"},
            {"key": "copilot-environment", "value": "staging"},
            {"key": "aws:cloudformation:logical-id", "value": "Cluster"},
        ]
    )["cluster"]["clusterArn"]

    assert not is_task_running(arn)

    client = boto3.client("ec2")
    images = client.describe_images(Owners=["amazon"])["Images"]
    client.run_instances(ImageId=images[0]["ImageId"], MinCount=1, MaxCount=1)
    instances = boto3.client("ec2").describe_instances()
    instance_id = instances["Reservations"][0]["Instances"][0]["InstanceId"]
    ec2 = boto3.resource("ec2")
    instance = ec2.Instance(instance_id)
    instance_id_document = json.dumps(ec2_utils.generate_instance_identity_document(instance))
    ecs_client.register_container_instance(cluster=arn, instanceIdentityDocument=instance_id_document)
    definition_arn = ecs_client.register_task_definition(
        family="copilot-dbtunnel",
        containerDefinitions=[
            {"name": "test_container", "image": "test_image", "cpu": 100, "memory": 500, "essential": True}
        ],
    )["taskDefinition"]["taskDefinitionArn"]
    ecs_client.run_task(cluster=arn, taskDefinition=definition_arn)

    assert is_task_running(arn)


@patch("os.system")
@patch("commands.conduit_cli.is_task_running", return_value=True)
def test_exec_into_task(is_task_running, system):
    """Test that exec_into_task runs the `copilot task exec` command with
    expected --app and --env flags."""

    exec_into_task("dbt-app", "staging", "arn:random")

    system.assert_called_once_with("copilot task exec --app dbt-app --env staging")


@freeze_time("Jan 14th, 2020", auto_tick_seconds=60)
def test_exec_into_task_timeout(capsys):
    exec_into_task("dbt-app", "staging", "arn:random")

    assert (
        capsys.readouterr().out
        == "Attempt to exec into running task timed out. Try again by running `copilot task exec --app dbt-app --env staging or check status of task in Amazon ECS console.\n"
    )


@mock_ecs
@mock_resourcegroupstaggingapi
@mock_sts
def test_tunnel_no_cluster_resource(alias_session):
    """Test that tunnel command prints an exit code when a cluster with app and
    env tags is not found."""

    runner = CliRunner()
    result = runner.invoke(tunnel, ["--project-profile", "foo", "--app", "dbt-app", "--env", "staging"])

    assert result.exit_code == 0
    assert "No cluster resource found with tag filter values dbt-app and staging" in result.output


@mock_sts
def test_tunnel_profile_not_configured():
    """Test that tunnel calls check_aws_conn and outputs expected error when AWS
    profile variable isn't set."""

    runner = CliRunner()
    result = runner.invoke(tunnel, ["--project-profile", "foo", "--app", "dbt-app", "--env", "staging"])

    assert 'AWS profile "foo" is not configured.' in result.output


@mock_ecs
@mock_resourcegroupstaggingapi
@mock_secretsmanager
@mock_sts
@patch("commands.conduit_cli.exec_into_task")
@patch("commands.conduit_cli.create_task")
def test_tunnel_task_not_running(create_task, exec_into_task, alias_session):
    """Test that, when a task is not already running, command creates and execs
    into a task."""

    cluster_arn = boto3.client("ecs").create_cluster(
        tags=[
            {"key": "copilot-application", "value": "dbt-app"},
            {"key": "copilot-environment", "value": "staging"},
            {"key": "aws:cloudformation:logical-id", "value": "Cluster"},
        ]
    )["cluster"]["clusterArn"]
    secret_arn = boto3.client("secretsmanager").create_secret(
        Name="/copilot/dbt-app/staging/secrets/POSTGRES", SecretString="secretivestring"
    )["ARN"]
    runner = CliRunner()
    runner.invoke(tunnel, ["--project-profile", "foo", "--app", "dbt-app", "--env", "staging"])

    create_task.assert_called_once_with("dbt-app", "staging", secret_arn)
    exec_into_task.assert_called_once_with("dbt-app", "staging", cluster_arn)


# patching is_task_running because it's tested separately above and requires a lot of moto legwork.
@mock_ecs
@mock_resourcegroupstaggingapi
@mock_secretsmanager
@mock_sts
@patch("commands.conduit_cli.is_task_running", return_value=True)
@patch("commands.conduit_cli.exec_into_task")
@patch("commands.conduit_cli.create_task")
def test_tunnel_task_already_running(create_task, exec_into_task, is_task_running, alias_session):
    """Test that, when a task is already running, command execs into this task
    and does not create a new one."""

    cluster_arn = boto3.client("ecs").create_cluster(
        tags=[
            {"key": "copilot-application", "value": "dbt-app"},
            {"key": "copilot-environment", "value": "staging"},
            {"key": "aws:cloudformation:logical-id", "value": "Cluster"},
        ]
    )["cluster"]["clusterArn"]
    runner = CliRunner()
    runner.invoke(tunnel, ["--project-profile", "foo", "--app", "dbt-app", "--env", "staging"])

    assert not create_task.called
    exec_into_task.assert_called_once_with("dbt-app", "staging", cluster_arn)
