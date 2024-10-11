# from unittest import mock
# from unittest.mock import patch
#
from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.database import dump
from dbt_platform_helper.commands.database import load

# import boto3
# import pytest
# from moto import mock_aws
# from dbt_platform_helper.utils.application import Application


@patch("dbt_platform_helper.commands.database.DatabaseCopy")
def test_command_dump_success(mock_database_copy_object):
    mock_database_copy_instance = mock_database_copy_object.return_value

    runner = CliRunner()
    result = runner.invoke(
        dump,
        [
            "--account-id",
            "12345",
            "--app",
            "my_app",
            "--env",
            "my_env",
            "--database",
            "my_postgres",
            "--vpc-name",
            "my_vpc",
        ],
    )

    assert result.exit_code == 0
    mock_database_copy_object.assert_called_once_with(
        "12345", "my_app", "my_env", "my_postgres", "my_vpc"
    )
    mock_database_copy_instance.dump.assert_called_once_with()


@patch("dbt_platform_helper.commands.database.DatabaseCopy")
def test_command_load_success(mock_database_copy_object):
    mock_database_copy_instance = mock_database_copy_object.return_value
    runner = CliRunner()
    result = runner.invoke(
        load,
        [
            "--account-id",
            "12345",
            "--app",
            "my_app",
            "--env",
            "my_env",
            "--database",
            "my_postgres",
            "--vpc-name",
            "my_vpc",
        ],
    )

    assert result.exit_code == 0
    mock_database_copy_object.assert_called_once_with(
        "12345", "my_app", "my_env", "my_postgres", "my_vpc"
    )
    mock_database_copy_instance.load.assert_called_once_with()


# @patch("dbt_platform_helper.commands.database.DatabaseCopy.dump")
# def test_command_dump_failure(mock_database_copy):
#     runner = CliRunner()
#     result = runner.invoke(
#         dump, ["--account-id", "12345", "--app", "my_app", "--env", "my_env", "--database", "my_postgres", "--vpc-name", "my_vpc"]
#     )
#
#     assert result.exit_code == 0
#     assert mock_database_copy.called_once()


# @mock_aws
# @patch(
#     "dbt_platform_helper.commands.database.get_aws_session_or_abort", return_value=boto3.Session()
# )
# @patch("click.confirm")
# @patch("subprocess.call")
# @patch(
#     "dbt_platform_helper.commands.database.get_connection_string",
#     return_value="test-connection-secret",
# )
# @patch("dbt_platform_helper.commands.database.get_cluster_arn", return_value="test-arn")
# @patch("dbt_platform_helper.commands.database.addon_client_is_running", return_value=False)
# @patch("dbt_platform_helper.commands.database.add_stack_delete_policy_to_task_role")
# @patch("dbt_platform_helper.commands.database.connect_to_addon_client_task")
# def test_copy(
#     connect_to_addon_client_task,
#     add_stack_delete_policy_to_task_role,
#     addon_client_is_running,
#     get_cluster_arn,
#     get_connection_string,
#     subprocess_call,
#     alias_session,
#     aws_credentials,
#     mock_application,
# ):
#     """Test that given a source and target database identifier, the copy command
#     copies data from source to target database."""
#     from dbt_platform_helper.commands.database import copy
#
#     source_db = f"{mock_application.name}-development-{mock_application.name}-postgres"
#     target_db = f"{mock_application.name}-staging-{mock_application.name}-postgres"
#
#     _setup_test_databases(source_db, mock_application, "development")
#     _setup_test_databases(target_db, mock_application, "staging")
#
#     task_name = f"database-copy-{mock_application.name}-development-{mock_application.name}-staging"
#
#     runner = CliRunner()
#     result = runner.invoke(
#         copy,
#         [
#             source_db,
#             target_db,
#         ],
#     )
#
#     subprocess_call.assert_called_once_with(
#         "copilot task run --app test-application --env development "
#         f"--task-group-name {task_name} "
#         f"--image public.ecr.aws/uktrade/tunnel:database-copy "
#         f"--env-vars SOURCE_DB_CONNECTION='test-connection-secret',TARGET_DB_CONNECTION='test-connection-secret' "
#         "--platform-os linux "
#         "--platform-arch arm64",
#         shell=True,
#     )
#
#     get_connection_string.assert_has_calls(
#         [
#             mock.call("test-application", "development", source_db),
#             mock.call("test-application", "staging", target_db),
#         ]
#     )
#
#     get_cluster_arn.assert_called_once_with(mock_application, "development")
#     addon_client_is_running.assert_called_with(
#         mock_application, "development", "test-arn", task_name
#     )
#     add_stack_delete_policy_to_task_role.assert_called_once_with(
#         mock_application, "development", task_name
#     )
#     connect_to_addon_client_task.assert_called_once_with(
#         mock_application, "development", "test-arn", task_name
#     )
#
#     assert f"Starting task to copy data from {source_db} to {target_db}" in result.output
#     assert result.exit_code == 0
#
#
# @pytest.mark.parametrize(
#     "source_env, target_env, error_message",
#     [
#         ("dev", "dev", "Source and target databases are the same."),
#         ("dev", "prod", "The target database cannot be a production database."),
#     ],
# )
# @mock_aws
# @patch(
#     "dbt_platform_helper.commands.database.get_aws_session_or_abort", return_value=boto3.Session()
# )
# @patch("click.confirm")
# def test_copy_command_fails_with_incorrect_environment_config(
#     alias_session,
#     aws_credentials,
#     mock_application,
#     source_env,
#     target_env,
#     error_message,
# ):
#     """Test that given source and target environments, the copy command fails
#     with the appropriate error message."""
#     from dbt_platform_helper.commands.database import copy
#
#     source_db = f"{mock_application.name}-{source_env}-{mock_application.name}-postgres"
#     target_db = f"{mock_application.name}-{target_env}-{mock_application.name}-postgres"
#
#     _setup_test_databases(source_db, mock_application, source_env)
#     _setup_test_databases(target_db, mock_application, target_env)
#
#     runner = CliRunner()
#     result = runner.invoke(
#         copy,
#         [
#             source_db,
#             target_db,
#         ],
#     )
#
#     assert error_message in result.output
#     assert result.exit_code == 1
#
#
# @mock_aws
# @patch(
#     "dbt_platform_helper.commands.database.get_aws_session_or_abort", return_value=boto3.Session()
# )
# @patch("click.confirm")
# def test_copy_command_fails_with_incorrect_database_identifier(
#     alias_session,
#     aws_credentials,
#     mock_application,
# ):
#     """Test that given an incorrect database identifier, the copy command fails
#     with the appropriate error message."""
#     from dbt_platform_helper.commands.database import copy
#
#     source_db = f"{mock_application.name}-development-{mock_application.name}-postgres"
#     target_db = f"{mock_application.name}-staging-{mock_application.name}-postgres"
#
#     _setup_test_databases("incorrect-identifier", mock_application, "development")
#     _setup_test_databases(target_db, mock_application, "staging")
#
#     runner = CliRunner()
#     result = runner.invoke(
#         copy,
#         [
#             source_db,
#             target_db,
#         ],
#     )
#
#     assert f"Database {source_db} not found. Check the database identifier." in result.output
#     assert result.exit_code == 1
#
#
# @mock_aws
# @patch(
#     "dbt_platform_helper.commands.database.get_aws_session_or_abort", return_value=boto3.Session()
# )
# @patch("click.confirm")
# def test_copy_command_fails_if_tags_not_found(
#     alias_session,
#     aws_credentials,
#     mock_application,
# ):
#     """Test that when the database does not have the correct tags, the copy
#     command fails with the appropriate error message."""
#     from dbt_platform_helper.commands.database import copy
#
#     source_db = f"{mock_application.name}-development-{mock_application.name}-postgres"
#     target_db = f"{mock_application.name}-staging-{mock_application.name}-postgres"
#
#     _setup_test_databases(source_db, mock_application, "development", False)
#     _setup_test_databases(target_db, mock_application, "staging")
#
#     runner = CliRunner()
#     result = runner.invoke(
#         copy,
#         [
#             source_db,
#             target_db,
#         ],
#     )
#
#     assert f"Required database tags not found." in result.output
#     assert result.exit_code == 1
#
#
# def _setup_test_databases(db_identifier: str, app: Application, env: str, with_tags: bool = True):
#     boto3.client("rds").create_db_instance(
#         DBName="main",
#         DBInstanceIdentifier=db_identifier,
#         DBInstanceClass="db.t3.micro",
#         Engine="postgres",
#         MasterUsername="postgres",
#         MasterUserPassword="password",
#         EngineVersion="16.2",
#         Tags=(
#             [
#                 {"Key": "copilot-application", "Value": app.name},
#                 {"Key": "copilot-environment", "Value": env},
#             ]
#             if with_tags
#             else []
#         ),
#     )
