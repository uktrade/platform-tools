from unittest.mock import patch

import boto3
import pytest
from moto import mock_ecs
from moto import mock_resourcegroupstaggingapi
from moto import mock_secretsmanager
from moto import mock_ssm

# from commands.conduit_cli import create_task
# from commands.conduit_cli import exec_into_task
# from commands.conduit_cli import get_cluster_arn
# from commands.conduit_cli import get_postgres_secret
# from commands.conduit_cli import get_secret_arn
# from commands.conduit_cli import is_task_running
# from commands.conduit_cli import tunnel
from commands.conduit_cli import NoClusterConduitError
from commands.conduit_cli import NoConnectionSecretError
from commands.conduit_cli import addon_client_is_running
from commands.conduit_cli import create_addon_client_task
from commands.conduit_cli import get_cluster_arn
from commands.conduit_cli import get_connection_secret_arn

# from moto import mock_secretsmanager
# from moto import mock_sts
# from moto.ec2 import utils as ec2_utils


# get_cluster_arn(app: str, env: str) -> str
# tests:
#   - test getting a cluster that exists
#   - test getting a cluster that does not exist


@mock_resourcegroupstaggingapi
def test_get_cluster_arn(mocked_cluster):
    """Test that, given app and environment strings, get_cluster_arn returns the
    arn of a cluster tagged with these strings."""

    assert get_cluster_arn("test-application", "development") == mocked_cluster["cluster"]["clusterArn"]


@mock_ecs
def test_get_cluster_arn_when_there_is_no_cluster():
    """Test that, given app and environment strings, get_cluster_arn raises an
    exception when no cluster tagged with these strings exists."""

    with pytest.raises(NoClusterConduitError):
        get_cluster_arn("test-application", "nope")


# get_connection_secret_arn(app: str, env: str, name: str) -> str
#   try boto3.client("secretsmanager").describe_secret(SecretId=secret_name)['ARN']
#   try boto3.client("ssm").get_parameter(Name=secret_name, WithDecryption=False)['Parameter']['ARN']
#   raise some type of error
#
# tests:
#   - test getting an existing secrets manager secret
#   - test getting an existing parameter secret
#   - test when neither parameter store or secrets manager has a value raises an error

# def test_get_secret_arn(mocked_pg_secret):
#     """Test that, given app, environment, and name strings, get_postgres_secret
#     returns the app's default named Postgres credentials from Secrets Manager."""
#     arn = get_secret_arn("dbt-app", "staging", "POSTGRES")
#
#     assert arn == mocked_pg_secret['ARN']


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

    assert arn == "arn:aws:ssm:eu-west-2:123456789012:parameter/copilot/test-application/development/secrets/POSTGRES"


@mock_secretsmanager
@mock_ssm
def test_get_connection_secret_arn_when_secret_does_not_exist():
    """Test that, given app, environment and secret name strings,
    get_connection_secret_arn raises an exception when no matching secret exists
    in secrets manager or parameter store."""
    with pytest.raises(NoConnectionSecretError):
        get_connection_secret_arn("test-application", "development", "POSTGRES")


# create_addon_client_task(app:str, env: str, addon_type: str, addon_name: str = None)
#   secret_arn = get_connection_secret_arn(app, env, (addon_name or addon_type).upper())
#
#   subprocess.call(f"copilot task run --app {app} --env {env} --name conduit-{addon_type} "
#                   f"--image {CONDUIT_DOCKER_IMAGE_LOCATION}:{addon_type} "
#                   f"--secrets CONNECTION_SECRET={secret_arn}", shell=True)
#
# tests:
#   - test subprocess.call is executed with addon_type for secret
#   - test subprocess.call is executed with addon_name for secret
#   - test subprocess.call is not executed when no connection secret is found


@patch("subprocess.call")
@patch("commands.conduit_cli.get_connection_secret_arn", return_value="test-arn")
def test_create_addon_client_task(get_connection_secret_arn, subprocess_call):
    """Test that, given app and environment strings, create_addon_client_task
    calls get_connection_secret_arn with the default secret name and
    subsequently subprocess.call with the correct secret ARN."""
    create_addon_client_task("test-application", "development", "postgres")

    get_connection_secret_arn.assert_called_once_with("test-application", "development", "POSTGRES")
    subprocess_call.assert_called_once_with(
        f"copilot task run --app test-application --env development --name conduit-postgres "
        f"--image public.ecr.aws/uktrade/tunnel:postgres "
        f"--secrets CONNECTION_SECRET=test-arn",
        shell=True,
    )


@patch("subprocess.call")
@patch("commands.conduit_cli.get_connection_secret_arn", return_value="test-named-arn")
def test_create_addon_client_task_with_addon_name(get_connection_secret_arn, subprocess_call):
    """Test that, given app, environment and secret name strings,
    create_addon_client_task calls get_connection_secret_arn with the custom
    secret name and subsequently subprocess.call with the correct secret ARN."""
    create_addon_client_task("test-application", "development", "postgres", "named-postgres")

    get_connection_secret_arn.assert_called_once_with("test-application", "development", "NAMED-POSTGRES")
    subprocess_call.assert_called_once_with(
        f"copilot task run --app test-application --env development --name conduit-postgres "
        f"--image public.ecr.aws/uktrade/tunnel:postgres "
        f"--secrets CONNECTION_SECRET=test-named-arn",
        shell=True,
    )


@patch("subprocess.call")
@patch("commands.conduit_cli.get_connection_secret_arn", side_effect=NoConnectionSecretError)
def test_create_addon_client_task_when_no_secret_found(get_connection_secret_arn, subprocess_call):
    """Test that, given app, environment and secret name strings,
    create_addon_client_task raises a NoConnectionSecretError and does not call
    subprocess.call."""
    with pytest.raises(NoConnectionSecretError):
        create_addon_client_task("test-application", "development", "postgres", "named-postgres")

        subprocess_call.assert_not_called()


# addon_client_is_running(app:str, env: str, cluster_arn: str, addon_type: str) -> bool
#
# tests:
#   - test list_tasks is called with the correct family based on addon_type
#   - test returns true when there is a running managed agent
#   - test returns false when no running managed agents


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_addon_client_is_running(mock_cluster_client_task, mocked_cluster, addon_type):
    mocked_cluster_for_client = mock_cluster_client_task(addon_type)
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]

    with patch("commands.conduit_cli.boto3.client", return_value=mocked_cluster_for_client):
        assert addon_client_is_running(mocked_cluster_arn, addon_type)


def test_addon_client_is_running_when_no_client_running():
    pass


# connect_to_addon_client_task(app:str, env: str, cluster_arn: str, addon_type: str)
#   wait until the client task is started and managed agent running
#   subprocess.call(f"copilot task exec --app {app} --env {env} --name conduit-{addon_type}", shell=True)
#
# tests:
#   - test subprocess.call executed when addon_client_is_running == True
#   - test subprocess.call not executed when addon_client_is_running == False and exception raised


def test_connect_to_addon_client_task(mock_cluster_client_task):
    pass


def test_connect_to_addon_client_task_when_timeout_reached():
    pass


# commands: postgres, redis, opensearch
# tests:
#   happy path --addon-name not specified
#   - test that get_cluster_arn is called
#   - test that create_addon_client_task is called without an addon_name
#   - test that get_connection_secret is called with addon_type
#   - test that addon_client_is_running is called with addon_type
#   - test that connect_to_addon_client_task is called with addon_type
#   happy path --addon-name specified
#   - test that get_cluster_arn is called
#   - test that create_addon_client_task is called with an addon_name
#   - test that get_connection_secret is called with addon_name
#   - test that addon_client_is_running is called with addon_type
#   - test that connect_to_addon_client_task is called with addon_type
#  sad path no cluster exists
#   - test that get_cluster_arn is called
#   - test that "no cluster for app or env exists" is logged
#   - test that command exits with non-zero code
#  sad path no secret exists --addon-name not specified
#   - test that get_connection_secret_arn is called with addon_type
#   - test that "no connection string for addon exists" is logged
#   - test that command exits with non-zero code
#  sad path no secret exists --addon-name specified
#   - test that get_connection_secret_arn is called with addon_name
#   - test that "no connection string for addon exists" is logged
#   - test that command exits with non-zero code
#  sad path task fails to start
#   - test that addon_client_is_running is called x times
#   - test that "addon client failed to start, check logs" is logged (should we print logs?)
#   - test that command exits with non-zero code


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_conduit_command(addon_type):
    pass


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_conduit_command_with_addon_name(addon_type):
    pass


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_conduit_command_when_no_cluster_exists(addon_type):
    pass


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_conduit_command_when_no_connection_secret_exists(addon_type):
    pass


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_conduit_command_when_no_connection_secret_exists_with_addon_name(addon_type):
    pass


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_conduit_command_when_client_task_fails_to_start(addon_type):
    pass


#
# def test_get_secret_arn(mocked_pg_secret):
#     """Test that, given app, environment, and name strings, get_postgres_secret
#     returns the app's default named Postgres credentials from Secrets Manager."""
#     arn = get_secret_arn("dbt-app", "staging", "POSTGRES")
#
#     assert arn == mocked_pg_secret['ARN']
#
#
# @mock_secretsmanager
# def test_get_secret_arn_with_custom_name():
#     """Test that, given app, environment, and name strings, get_postgres_secret
#     returns the app's custom named Postgres credentials from Secrets Manager."""
#     mocked_secretsmanager = boto3.client("secretsmanager")
#
#     secret_resource = {
#         "Name": "/copilot/dbt-app/staging/secrets/custom-name",
#         "Description": "A test parameter",
#         "SecretString": 'A test secret',
#     }
#
#     mocked_secretsmanager.create_secret(**secret_resource)
#
#     arn_response = get_secret_arn("dbt-app", "staging", "custom-name")
#
#     assert arn_response.startswith('arn:aws:secretsmanager:eu-west-2:123456789012:secret:/copilot/dbt-app/staging'
#                                    '/secrets/custom-name-')
#
#
# @patch("subprocess.call")
# def test_create_task(subprocess_call, mocked_pg_secret):
#     """Test that create_task runs the `copilot task run` command with expected
#     --app and --env flags."""
#
#     expected_arn = mocked_pg_secret["ARN"]
#     create_task("dbt-app", "staging", "POSTGRES")
#
#     subprocess_call.assert_called_once_with(
#         f"copilot task run -n dbtunnel --image public.ecr.aws/uktrade/tunnel --secrets DB_SECRET={expected_arn} --env-vars POSTGRES_PASSWORD=abc123 --app dbt-app --env staging",
#         shell=True,
#     )
#
#
# def test_get_postgres_secret(mocked_pg_secret):
#     """Test that, given app and environment strings, get_postgres_secret returns
#     the app's secret arn string."""
#
#     expected_arn = mocked_pg_secret["ARN"]
#     secret_response = get_postgres_secret("dbt-app", "staging", "POSTGRES")
#
#     assert secret_response["ARN"] == expected_arn
#     assert (
#         secret_response["SecretString"]
#         == '{"password":"abc123","dbname":"main","engine":"postgres","port":5432,"dbInstanceIdentifier":"dbt-app-staging-addons-postgresdbinstance-blah","host":"dbt-app-staging-addons-postgresdbinstance-blah.whatever.eu-west-2.rds.amazonaws.com","username":"postgres"}'
#     )
#     assert secret_response["Name"] == "/copilot/dbt-app/staging/secrets/POSTGRES"
#
#
# @mock_secretsmanager
# def test_get_postgres_secret_with_custom_name():
#     """Test that, given app, environment, and name strings, get_postgres_secret
#     returns the app's custom named Postgres credentials from Secrets Manager."""
#     mocked_secretsmanager = boto3.client("secretsmanager")
#
#     secret_resource = {
#         "Name": "/copilot/dbt-app/staging/secrets/custom-name",
#         "Description": "A test parameter",
#         "SecretString": '{"password":"abc123","dbname":"main","engine":"postgres","port":5432,"dbInstanceIdentifier":"dbt-app-staging-addons-postgresdbinstance-blah","host":"dbt-app-staging-addons-postgresdbinstance-blah.whatever.eu-west-2.rds.amazonaws.com","username":"postgres"}',
#     }
#
#     mocked_secretsmanager.create_secret(**secret_resource)
#
#     secret_response = get_postgres_secret("dbt-app", "staging", "custom-name")
#
#     assert secret_response["SecretString"] == secret_resource["SecretString"]
#     assert secret_response["Name"] == secret_resource["Name"]
#
#
# def test_is_task_running_when_task_is_not_running(mocked_cluster):
#     """Given an ECS Cluster ARN string, is_task_running should return False when
#     the task is not running."""
#
#     assert not is_task_running(mocked_cluster["cluster"]["clusterArn"])
#
#
# @mock_ec2
# def test_is_task_running(mocked_cluster):
#     """Given an ECS Cluster ARN string, is_task_running should return True when
#     the task is running."""
#
#     # Create mocked ECS Cluster
#     mocked_ecs_client = boto3.client("ecs")
#     mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
#     # Create mocked EC2 instance
#     mocked_ec2_client = boto3.client("ec2")
#     mocked_ec2_images = mocked_ec2_client.describe_images(Owners=["amazon"])["Images"]
#     mocked_ec2_client.run_instances(ImageId=mocked_ec2_images[0]["ImageId"], MinCount=1, MaxCount=1)
#     mocked_ec2_instances = boto3.client("ec2").describe_instances()
#     mocked_ec2_instance_id = mocked_ec2_instances["Reservations"][0]["Instances"][0]["InstanceId"]
#     mocked_ec2 = boto3.resource("ec2")
#     mocked_ec2_instance = mocked_ec2.Instance(mocked_ec2_instance_id)
#     mocked_instance_id_document = json.dumps(ec2_utils.generate_instance_identity_document(mocked_ec2_instance))
#     # Attach mocked EC2 instance to the mocked ECS Cluster
#     mocked_ecs_client.register_container_instance(
#         cluster=mocked_cluster_arn, instanceIdentityDocument=mocked_instance_id_document
#     )
#     mocked_task_definition_arn = mocked_ecs_client.register_task_definition(
#         family="copilot-dbtunnel",
#         containerDefinitions=[
#             {"name": "test_container", "image": "test_image", "cpu": 100, "memory": 500, "essential": True}
#         ],
#     )["taskDefinition"]["taskDefinitionArn"]
#     mocked_ecs_client.run_task(
#         cluster=mocked_cluster_arn, taskDefinition=mocked_task_definition_arn, enableExecuteCommand=True
#     )
#
#     # moto does not yet provide the ability to mock an executable task and its managed agents / containers, so we need to patch the expected response
#     def describe_tasks(cluster, tasks):
#         return {
#             "tasks": [
#                 {
#                     "lastStatus": "RUNNING",
#                     "containers": [{"managedAgents": [{"name": "ExecuteCommandAgent", "lastStatus": "RUNNING"}]}],
#                 }
#             ]
#         }
#
#     mocked_ecs_client.describe_tasks = describe_tasks
#
#     with patch("commands.conduit_cli.boto3.client", return_value=mocked_ecs_client):
#         assert is_task_running(mocked_cluster_arn)
#
#
# @patch("os.system")
# @patch("commands.conduit_cli.is_task_running", return_value=True)
# def test_exec_into_task(is_task_running, system):
#     """Test that exec_into_task runs the `copilot task exec` command with
#     expected --app and --env flags."""
#
#     exec_into_task("dbt-app", "staging", "arn:random")
#
#     system.assert_called_once_with("copilot task exec --app dbt-app --env staging")
#
#
# @freeze_time("Jan 14th, 2020", auto_tick_seconds=60)
# def test_exec_into_task_timeout(capsys):
#     exec_into_task("dbt-app", "staging", "arn:random")
#
#     assert (
#         capsys.readouterr().out
#         == "Attempt to exec into running task timed out. Try again by running `copilot task exec --app dbt-app --env staging` or check status of task in Amazon ECS console.\n"
#     )
#
#
# @mock_ecs
# @mock_resourcegroupstaggingapi
# @mock_sts
# def test_tunnel_no_cluster_resource(alias_session):
#     """Test that tunnel command prints an exit code when a cluster with app and
#     env tags is not found."""
#
#     result = CliRunner().invoke(tunnel, ["--project-profile", "foo", "--app", "dbt-app", "--env", "staging"])
#
#     assert result.exit_code == 0
#     assert "No cluster resource found with tag filter values dbt-app and staging" in result.output
#
#
# @mock_sts
# def test_tunnel_profile_not_configured():
#     """Test that tunnel calls check_aws_conn and outputs expected error when AWS
#     profile isn't configured."""
#
#     result = CliRunner().invoke(tunnel, ["--project-profile", "foo", "--app", "dbt-app", "--env", "staging"])
#
#     assert 'AWS profile "foo" is not configured.' in result.output
#
#
# @mock_resourcegroupstaggingapi
# @mock_sts
# @patch("commands.conduit_cli.exec_into_task")
# @patch("commands.conduit_cli.create_task")
# def test_tunnel_task_not_running(create_task, exec_into_task, alias_session, mocked_cluster, mocked_pg_secret):
#     """Test that, when a task is not already running, command creates and execs
#     into a task."""
#
#     cluster_arn = mocked_cluster["cluster"]["clusterArn"]
#
#     CliRunner().invoke(tunnel, ["--project-profile", "foo", "--app", "dbt-app", "--env", "staging"])
#
#     create_task.assert_called_once_with("dbt-app", "staging", "POSTGRES")
#     exec_into_task.assert_called_once_with("dbt-app", "staging", cluster_arn)
#
#
# # patching is_task_running because it's tested separately above and requires a lot of moto legwork.
# @mock_resourcegroupstaggingapi
# @mock_secretsmanager
# @mock_sts
# @patch("commands.conduit_cli.is_task_running", return_value=True)
# @patch("commands.conduit_cli.exec_into_task")
# @patch("commands.conduit_cli.create_task")
# def test_tunnel_task_already_running(create_task, exec_into_task, is_task_running, alias_session, mocked_cluster):
#     """Test that, when a task is already running, command execs into this task
#     and does not create a new one."""
#
#     cluster_arn = mocked_cluster["cluster"]["clusterArn"]
#
#     CliRunner().invoke(tunnel, ["--project-profile", "foo", "--app", "dbt-app", "--env", "staging"])
#
#     assert not create_task.called
#     exec_into_task.assert_called_once_with("dbt-app", "staging", cluster_arn)
#
#
# @mock_resourcegroupstaggingapi
# @mock_sts
# @patch("commands.conduit_cli.exec_into_task")
# @patch("commands.conduit_cli.create_task")
# def test_tunnel_task_with_custom_db_secret_name(
#     create_task, exec_into_task, alias_session, mocked_cluster, mocked_pg_secret
# ):
#     """Test that, when a task is not already running, command creates and execs
#     into a task with optional --db-secret-name flag."""
#
#     cluster_arn = mocked_cluster["cluster"]["clusterArn"]
#
#     CliRunner().invoke(
#         tunnel,
#         [
#             "--project-profile",
#             "foo",
#             "--app",
#             "dbt-app",
#             "--env",
#             "staging",
#             "--db-secret-name",
#             "custom-db-secret-name",
#         ],
#     )
#
#     create_task.assert_called_once_with("dbt-app", "staging", "custom-db-secret-name")
#     exec_into_task.assert_called_once_with("dbt-app", "staging", cluster_arn)
#
#
# @mock_resourcegroupstaggingapi
# @mock_secretsmanager
# @mock_sts
# @patch("commands.conduit_cli.is_task_running", return_value=False)
# def test_tunnel_secret_not_found(is_task_running, alias_session, mocked_cluster):
#     result = CliRunner().invoke(tunnel, ["--project-profile", "foo", "--app", "dbt-app", "--env", "staging"])
#
#     assert "No secret found matching application dbt-app and environment staging." in result.output
