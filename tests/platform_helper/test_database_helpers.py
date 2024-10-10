from unittest.mock import Mock

import pytest

from dbt_platform_helper.commands.database_helpers import DatabaseCopy
from dbt_platform_helper.commands.database_helpers import run_database_copy_task
from dbt_platform_helper.utils.aws import Vpc


@pytest.mark.parametrize("is_dump, exp_operation", [(True, "dump"), (False, "load")])
def test_run_database_copy_task(is_dump, exp_operation):
    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client

    account_id = "1234567"
    app = "my_app"
    env = "my_env"
    database = "my_postgres"
    vpc_config = Vpc(["subnet_1", "subnet_2"], ["sec_group_1"])
    db_connection_string = "connection_string"

    run_database_copy_task(
        mock_session, account_id, app, env, database, vpc_config, is_dump, db_connection_string
    )

    mock_session.client.assert_called_once_with("ecs")
    mock_client.run_task.assert_called_once_with(
        taskDefinition=f"arn:aws:ecs:eu-west-2:1234567:task-definition/my_env-my_postgres-{exp_operation}",
        cluster="my_app-my_env",
        capacityProviderStrategy=[
            {"capacityProvider": "FARGATE", "weight": 1, "base": 0},
        ],
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": ["subnet_1", "subnet_2"],
                "securityGroups": [
                    "sec_group_1",
                ],
                "assignPublicIp": "DISABLED",
            }
        },
        overrides={
            "containerOverrides": [
                {
                    "name": f"my_env-my_postgres-{exp_operation}",
                    "environment": [
                        {"name": "DATA_COPY_OPERATION", "value": exp_operation.upper()},
                        {"name": "DB_CONNECTION_STRING", "value": "connection_string"},
                    ],
                }
            ]
        },
    )


def test_database_dump():
    app = "my-app"
    env = "my-env"
    vpc_name = "test-vpc"
    database = "test-db"

    account_id = "1234567"

    mock_session = Mock()
    mock_session_fn = Mock(return_value=mock_session)
    mock_run_database_copy_task_fn = Mock()

    vpc = Vpc([], [])
    mock_vpc_config_fn = Mock()
    mock_vpc_config_fn.return_value = vpc
    mock_db_connection_string_fn = Mock(return_value="test-db-connection-string")

    db_copy = DatabaseCopy(
        mock_session_fn,
        mock_run_database_copy_task_fn,
        mock_vpc_config_fn,
        mock_db_connection_string_fn,
    )
    db_copy.dump(account_id, app, env, database, vpc_name)

    mock_session_fn.assert_called_once()

    mock_vpc_config_fn.assert_called_once_with(mock_session, app, env, vpc_name)

    mock_db_connection_string_fn.assert_called_once_with(mock_session, app, env, "test-db")

    mock_run_database_copy_task_fn.assert_called_once_with(
        mock_session, account_id, app, env, database, vpc, True, "test-db-connection-string"
    )


def test_database_load():
    app = "my-app"
    env = "my-env"
    vpc_name = "test-vpc"
    database = "test-db"

    account_id = "1234567"

    mock_session = Mock()
    mock_session_fn = Mock(return_value=mock_session)
    mock_run_database_copy_task_fn = Mock()

    vpc = Vpc([], [])
    mock_vpc_config_fn = Mock()
    mock_vpc_config_fn.return_value = vpc
    mock_db_connection_string_fn = Mock(return_value="test-db-connection-string")

    db_copy = DatabaseCopy(
        mock_session_fn,
        mock_run_database_copy_task_fn,
        mock_vpc_config_fn,
        mock_db_connection_string_fn,
    )
    db_copy.load(account_id, app, env, database, vpc_name)

    mock_session_fn.assert_called_once()

    mock_vpc_config_fn.assert_called_once_with(mock_session, app, env, vpc_name)

    mock_db_connection_string_fn.assert_called_once_with(mock_session, app, env, "test-db")

    mock_run_database_copy_task_fn.assert_called_once_with(
        mock_session, account_id, app, env, database, vpc, False, "test-db-connection-string"
    )
