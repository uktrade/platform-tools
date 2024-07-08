from unittest.mock import patch

import boto3
from click.testing import CliRunner
from moto import mock_aws

from dbt_platform_helper.utils.application import Application


@mock_aws
@patch(
    "dbt_platform_helper.commands.database.get_aws_session_or_abort", return_value=boto3.Session()
)
@patch("click.confirm")
@patch("subprocess.call")
@patch(
    "dbt_platform_helper.commands.database.get_connection_string",
    return_value="test-connection-secret",
)
@patch("dbt_platform_helper.commands.database.get_cluster_arn", return_value="test-arn")
@patch("dbt_platform_helper.commands.database.addon_client_is_running", return_value=False)
@patch("dbt_platform_helper.commands.database.add_stack_delete_policy_to_task_role")
@patch("dbt_platform_helper.commands.database.connect_to_addon_client_task")
def test_copy(
    connect_to_addon_client_task,
    add_stack_delete_policy_to_task_role,
    addon_client_is_running,
    get_cluster_arn,
    get_connection_string,
    subprocess_call,
    alias_session,
    aws_credentials,
    mock_application,
):
    """Test that given a source and target database identifier, the copy command
    copies data from source to target database."""
    from dbt_platform_helper.commands.database import copy

    source_db = f"{mock_application.name}-development-{mock_application.name}-postgres"
    target_db = f"{mock_application.name}-staging-{mock_application.name}-postgres"

    _setup_test_databases(source_db, mock_application, "development")
    _setup_test_databases(target_db, mock_application, "staging")

    task_name = f"database-copy-{mock_application.name}-development-{mock_application.name}-staging"

    runner = CliRunner()
    result = runner.invoke(
        copy,
        [
            "--source-db",
            source_db,
            "--target-db",
            target_db,
        ],
    )

    subprocess_call.assert_called_once_with(
        "copilot task run --app test-application --env development "
        f"--task-group-name {task_name} "
        f"--image public.ecr.aws/uktrade/tunnel:database-copy "
        f"--env-vars SOURCE_DB_CONNECTION='test-connection-secret',TARGET_DB_CONNECTION='test-connection-secret' "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )

    get_cluster_arn.assert_called_once_with(mock_application, "development")
    addon_client_is_running.assert_called_with(
        mock_application, "development", "test-arn", task_name
    )
    add_stack_delete_policy_to_task_role.assert_called_once_with(
        mock_application, "development", task_name
    )
    connect_to_addon_client_task.assert_called_once_with(
        mock_application, "development", "test-arn", task_name
    )

    assert f"Starting task to copy data from {source_db} to {target_db}" in result.output
    assert result.exit_code == 0


def _setup_test_databases(db_identifier: str, app: Application, env: str):
    boto3.client("rds").create_db_instance(
        DBName="main",
        DBInstanceIdentifier=db_identifier,
        DBInstanceClass="db.t3.micro",
        Engine="postgres",
        MasterUsername="postgres",
        MasterUserPassword="password",
        EngineVersion="16.2",
        Tags=[
            {"Key": "copilot-application", "Value": app.name},
            {"Key": "copilot-environment", "Value": env},
        ],
    )

    # boto3.client("ssm").put_parameter(
    #     Name=f"/copilot/test-application/{env}/secrets/TEST_APPLICATION_POSTGRES_READ_ONLY_USER",
    #     Type="String",
    #     Value=f'{{\"username": "postgres", "password": "password", "engine": "postgres", "port": 5432, "dbname": '
    #           f'"main", "host": "{db_identifier}.eu-west-2.rds.amazonaws.com", "dbInstanceIdentifi'
    #           f'er": "{db_identifier}"}}'
    # )
    #
    # boto3.client("ssm").put_parameter(
    #     Name=f"/copilot/test-application/{env}/secrets/TEST_APPLICATION_POSTGRES_RDS_MASTER_ARN",
    #     Type="String",
    #     Value="mock-master-user-arn",
    # )
    #
    # boto3.client("secretsmanager").create_secret(
    #     Name=f"rds!test-{env}-rds-master-user-secret",
    #     SecretString='{"username":"postgres","password":"password"}',
    # )
