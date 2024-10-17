from unittest.mock import Mock
from unittest.mock import call

import pytest

from dbt_platform_helper.commands.database_helpers import DatabaseCopy
from dbt_platform_helper.commands.database_helpers import run_database_copy_task
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.aws import Vpc


@pytest.mark.parametrize("is_dump, exp_operation", [(True, "dump"), (False, "load")])
def test_run_database_copy_task(is_dump, exp_operation):
    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.run_task.return_value = {"tasks": [{"taskArn": "arn:aws:ecs:test-task-arn"}]}

    account_id = "1234567"
    app = "my_app"
    env = "my_env"
    database = "my_postgres"
    vpc_config = Vpc(["subnet_1", "subnet_2"], ["sec_group_1"])
    db_connection_string = "connection_string"

    actual_task_arn = run_database_copy_task(
        mock_session, account_id, app, env, database, vpc_config, is_dump, db_connection_string
    )

    assert actual_task_arn == "arn:aws:ecs:test-task-arn"

    mock_session.client.assert_called_once_with("ecs")
    mock_client.run_task.assert_called_once_with(
        taskDefinition=f"arn:aws:ecs:eu-west-2:1234567:task-definition/my_app-my_env-my_postgres-{exp_operation}",
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
                    "name": f"my_app-my_env-my_postgres-{exp_operation}",
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

    mock_application = Application(app)
    mock_environment = Mock()
    mock_application.environments = {env: mock_environment}
    mock_load_application_fn = Mock(return_value=mock_application)

    mock_run_database_copy_task_fn = Mock(return_value="arn://task-arn")

    vpc = Vpc([], [])
    mock_vpc_config_fn = Mock()
    mock_vpc_config_fn.return_value = vpc
    mock_db_connection_string_fn = Mock(return_value="test-db-connection-string")

    mock_input_fn = Mock(return_value="yes")
    mock_echo_fn = Mock()

    db_copy = DatabaseCopy(
        account_id,
        app,
        database,
        mock_load_application_fn,
        mock_run_database_copy_task_fn,
        mock_vpc_config_fn,
        mock_db_connection_string_fn,
        mock_input_fn,
        mock_echo_fn,
    )

    db_copy.tail_logs = Mock()

    db_copy.dump(env, vpc_name)

    mock_load_application_fn.assert_called_once()
    mock_vpc_config_fn.assert_called_once_with(mock_environment.session, app, env, vpc_name)
    mock_db_connection_string_fn.assert_called_once_with(
        mock_environment.session, app, env, "my-app-my-env-test-db"
    )
    mock_run_database_copy_task_fn.assert_called_once_with(
        mock_environment.session,
        account_id,
        app,
        env,
        database,
        vpc,
        True,
        "test-db-connection-string",
    )
    mock_input_fn.assert_not_called()
    mock_echo_fn.assert_has_calls(
        [
            call("Dumping test-db from the my-env environment into S3", fg="white", bold=True),
            call(
                "Task arn://task-arn started. Waiting for it to complete (this may take some time)...",
                fg="green",
            ),
        ]
    )
    db_copy.tail_logs.assert_called_once_with(True, env)


def test_database_load_with_response_of_yes():
    app = "my-app"
    env = "my-env"
    vpc_name = "test-vpc"
    database = "test-db"

    account_id = "1234567"

    mock_application = Application(app)
    mock_environment = Mock()
    mock_application.environments = {env: mock_environment}
    mock_load_application_fn = Mock(return_value=mock_application)

    mock_run_database_copy_task_fn = Mock(return_value="arn://task-arn")

    vpc = Vpc([], [])
    mock_vpc_config_fn = Mock()
    mock_vpc_config_fn.return_value = vpc
    mock_db_connection_string_fn = Mock(return_value="test-db-connection-string")

    mock_input_fn = Mock(return_value="yes")
    mock_echo_fn = Mock()

    db_copy = DatabaseCopy(
        account_id,
        app,
        database,
        mock_load_application_fn,
        mock_run_database_copy_task_fn,
        mock_vpc_config_fn,
        mock_db_connection_string_fn,
        mock_input_fn,
        mock_echo_fn,
    )
    db_copy.tail_logs = Mock()

    db_copy.load(env, vpc_name)

    mock_load_application_fn.assert_called_once()

    mock_vpc_config_fn.assert_called_once_with(mock_environment.session, app, env, vpc_name)

    mock_db_connection_string_fn.assert_called_once_with(
        mock_environment.session, app, env, "my-app-my-env-test-db"
    )

    mock_run_database_copy_task_fn.assert_called_once_with(
        mock_environment.session,
        account_id,
        app,
        env,
        database,
        vpc,
        False,
        "test-db-connection-string",
    )

    mock_input_fn.assert_called_once_with(
        f"Are all tasks using test-db in the my-env environment stopped? (y/n)"
    )

    mock_echo_fn.assert_has_calls(
        [
            call(
                "Loading data into test-db in the my-env environment from S3", fg="white", bold=True
            ),
            call(
                "Task arn://task-arn started. Waiting for it to complete (this may take some time)...",
                fg="green",
            ),
        ]
    )
    db_copy.tail_logs.assert_called_once_with(False, "my-env")


def test_database_load_with_response_of_no():
    app = "my-app"
    env = "my-env"
    vpc_name = "test-vpc"
    database = "test-db"

    account_id = "1234567"

    mock_application = Application(app)
    mock_environment = Mock()
    mock_application.environments = {env: mock_environment}
    mock_load_application_fn = Mock(return_value=mock_application)

    mock_run_database_copy_task_fn = Mock()

    vpc = Vpc([], [])
    mock_vpc_config_fn = Mock()
    mock_vpc_config_fn.return_value = vpc
    mock_db_connection_string_fn = Mock(return_value="test-db-connection-string")

    mock_input_fn = Mock(return_value="no")
    mock_echo_fn = Mock()

    db_copy = DatabaseCopy(
        account_id,
        app,
        database,
        mock_load_application_fn,
        mock_run_database_copy_task_fn,
        mock_vpc_config_fn,
        mock_db_connection_string_fn,
        mock_input_fn,
        mock_echo_fn,
    )
    db_copy.tail_logs = Mock()

    db_copy.load(env, vpc_name)

    mock_environment.session_fn.assert_not_called()

    mock_vpc_config_fn.assert_not_called()

    mock_db_connection_string_fn.assert_not_called()

    mock_run_database_copy_task_fn.assert_not_called()

    mock_input_fn.assert_called_once_with(
        f"Are all tasks using test-db in the my-env environment stopped? (y/n)"
    )
    mock_echo_fn.assert_not_called()
    db_copy.tail_logs.assert_not_called()


@pytest.mark.parametrize("user_response", ["y", "Y", " y ", "\ny", "YES", "yes"])
def test_is_confirmed_ready_to_load(user_response):
    mock_input = Mock()
    mock_input.return_value = user_response
    db_copy = DatabaseCopy(
        "",
        "",
        "test-db",
        Mock(),
        None,
        None,
        None,
        mock_input,
    )

    assert db_copy.is_confirmed_ready_to_load("test-env")

    mock_input.assert_called_once_with(
        f"Are all tasks using test-db in the test-env environment stopped? (y/n)"
    )


@pytest.mark.parametrize("user_response", ["n", "N", " no ", "squiggly"])
def test_is_not_confirmed_ready_to_load(user_response):
    mock_input = Mock()
    mock_input.return_value = user_response
    db_copy = DatabaseCopy(
        None,
        None,
        "test-db",
        Mock(),
        None,
        None,
        None,
        mock_input,
    )

    assert not db_copy.is_confirmed_ready_to_load("test-env")

    mock_input.assert_called_once_with(
        f"Are all tasks using test-db in the test-env environment stopped? (y/n)"
    )


@pytest.mark.parametrize("is_dump", [True, False])
def test_tail_logs(is_dump):
    action = "dump" if is_dump else "load"

    mock_application = Application("test-app")
    mock_environment = Mock()
    mock_application.environments = {"test-env": mock_environment}
    mock_load_application_fn = Mock(return_value=mock_application)
    mock_client = Mock()

    mock_environment.session.client.return_value = mock_client

    mock_client.start_live_tail.return_value = {
        "responseStream": [
            {"sessionStart": {}},
            {"sessionUpdate": {"sessionResults": []}},
            {"sessionUpdate": {"sessionResults": [{"message": ""}]}},
            {"sessionUpdate": {"sessionResults": [{"message": f"Starting data {action}"}]}},
            {"sessionUpdate": {"sessionResults": [{"message": "A load of SQL shenanigans"}]}},
            {"sessionUpdate": {"sessionResults": [{"message": f"Stopping data {action}"}]}},
        ]
    }
    mock_echo = Mock()

    db_copy = DatabaseCopy(
        "1234",
        "test-app",
        "test-db",
        mock_load_application_fn,
        None,
        None,
        None,
        None,
        echo_fn=mock_echo,
    )
    db_copy.tail_logs(is_dump, "test-env")

    mock_environment.session.client.assert_called_once_with("logs")
    mock_client.start_live_tail.assert_called_once_with(
        logGroupIdentifiers=[
            f"arn:aws:logs:eu-west-2:1234:log-group:/ecs/test-app-test-env-test-db-{action}"
        ],
    )

    mock_echo.assert_has_calls(
        [
            call(
                f"Tailing logs for /ecs/test-app-test-env-test-db-{action}",
                fg="yellow",
            ),
            call(f"Starting data {action}"),
            call("A load of SQL shenanigans"),
            call(f"Stopping data {action}"),
        ]
    )
