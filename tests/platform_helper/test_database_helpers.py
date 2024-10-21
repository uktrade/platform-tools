from unittest.mock import Mock
from unittest.mock import call

import pytest

from dbt_platform_helper.commands.database_helpers import DatabaseCopy
from dbt_platform_helper.exceptions import AWSException
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import ApplicationNotFoundError
from dbt_platform_helper.utils.aws import Vpc


class Mocks:
    def __init__(self, app="test-app", env="test-env", acc="12345", vpc=Vpc([], [])):
        self.application = Application(app)
        self.environment = Mock()
        self.environment.account_id = acc
        self.application.environments = {env: self.environment, "test-env-2": Mock()}
        self.load_application_fn = Mock(return_value=self.application)
        self.client = Mock()
        self.environment.session.client.return_value = self.client

        self.vpc = vpc
        self.vpc_config_fn = Mock()
        self.vpc_config_fn.return_value = vpc
        self.db_connection_string_fn = Mock(return_value="test-db-connection-string")

        self.input_fn = Mock(return_value="yes")
        self.echo_fn = Mock()
        self.abort_fn = Mock(side_effect=SystemExit(1))


@pytest.mark.parametrize("is_dump, exp_operation", [(True, "dump"), (False, "load")])
def test_run_database_copy_task(is_dump, exp_operation):
    app = "test-app"
    env = "test-env"
    database = "test-postgres"
    vpc = Vpc(["subnet_1", "subnet_2"], ["sec_group_1"])
    mocks = Mocks(app, env, vpc=vpc)
    db_connection_string = "connection_string"

    db_copy = DatabaseCopy(
        app,
        database,
        load_application_fn=mocks.load_application_fn,
        vpc_config_fn=mocks.vpc_config_fn,
        db_connection_string_fn=mocks.db_connection_string_fn,
        input_fn=mocks.input_fn,
        echo_fn=mocks.echo_fn,
    )

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.run_task.return_value = {"tasks": [{"taskArn": "arn:aws:ecs:test-task-arn"}]}

    actual_task_arn = db_copy.run_database_copy_task(
        mock_session, env, vpc, is_dump, db_connection_string
    )

    assert actual_task_arn == "arn:aws:ecs:test-task-arn"

    mock_session.client.assert_called_once_with("ecs")
    mock_client.run_task.assert_called_once_with(
        taskDefinition=f"arn:aws:ecs:eu-west-2:12345:task-definition/test-app-test-env-test-postgres-{exp_operation}",
        cluster="test-app-test-env",
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
                    "name": f"test-app-test-env-test-postgres-{exp_operation}",
                    "environment": [
                        {"name": "DATA_COPY_OPERATION", "value": exp_operation.upper()},
                        {"name": "DB_CONNECTION_STRING", "value": "connection_string"},
                    ],
                }
            ]
        },
    )


def test_database_dump():
    app = "test-app"
    env = "test-env"
    vpc_name = "test-vpc"
    database = "test-db"

    mocks = Mocks(app, env)

    mock_run_database_copy_task = Mock(return_value="arn://task-arn")

    db_copy = DatabaseCopy(
        app,
        database,
        mocks.load_application_fn,
        mocks.vpc_config_fn,
        mocks.db_connection_string_fn,
        mocks.input_fn,
        mocks.echo_fn,
    )
    db_copy.run_database_copy_task = mock_run_database_copy_task

    db_copy.tail_logs = Mock()

    db_copy.dump(env, vpc_name)

    mocks.load_application_fn.assert_called_once()
    mocks.vpc_config_fn.assert_called_once_with(mocks.environment.session, app, env, vpc_name)
    mocks.db_connection_string_fn.assert_called_once_with(
        mocks.environment.session, app, env, "test-app-test-env-test-db"
    )
    mock_run_database_copy_task.assert_called_once_with(
        mocks.environment.session,
        env,
        mocks.vpc,
        True,
        "test-db-connection-string",
    )
    mocks.input_fn.assert_not_called()
    mocks.echo_fn.assert_has_calls(
        [
            call("Dumping test-db from the test-env environment into S3", fg="white", bold=True),
            call(
                "Task arn://task-arn started. Waiting for it to complete (this may take some time)...",
                fg="white",
            ),
        ]
    )
    db_copy.tail_logs.assert_called_once_with(True, env)


def test_database_load_with_response_of_yes():
    app = "test-app"
    env = "test-env"
    vpc_name = "test-vpc"
    database = "test-db"

    mocks = Mocks()

    mock_run_database_copy_task = Mock(return_value="arn://task-arn")

    vpc = Vpc([], [])
    mock_vpc_config_fn = Mock()
    mock_vpc_config_fn.return_value = vpc
    mock_db_connection_string_fn = Mock(return_value="test-db-connection-string")

    db_copy = DatabaseCopy(
        app,
        database,
        mocks.load_application_fn,
        mock_vpc_config_fn,
        mock_db_connection_string_fn,
        mocks.input_fn,
        mocks.echo_fn,
    )
    db_copy.tail_logs = Mock()
    db_copy.run_database_copy_task = mock_run_database_copy_task

    db_copy.load(env, vpc_name)

    mocks.load_application_fn.assert_called_once()

    mock_vpc_config_fn.assert_called_once_with(mocks.environment.session, app, env, vpc_name)

    mock_db_connection_string_fn.assert_called_once_with(
        mocks.environment.session, app, env, "test-app-test-env-test-db"
    )

    mock_run_database_copy_task.assert_called_once_with(
        mocks.environment.session,
        env,
        vpc,
        False,
        "test-db-connection-string",
    )

    mocks.input_fn.assert_called_once_with(
        f"\nAre all tasks using test-db in the test-env environment stopped? (y/n)"
    )

    mocks.echo_fn.assert_has_calls(
        [
            call(
                "Loading data into test-db in the test-env environment from S3",
                fg="white",
                bold=True,
            ),
            call(
                "Task arn://task-arn started. Waiting for it to complete (this may take some time)...",
                fg="white",
            ),
        ]
    )
    db_copy.tail_logs.assert_called_once_with(False, "test-env")


def test_database_load_with_response_of_no():
    app = "test-app"
    env = "test-env"
    vpc_name = "test-vpc"
    database = "test-db"

    mocks = Mocks(app, env)
    mocks.input_fn = Mock(return_value="no")

    mock_run_database_copy_task_fn = Mock()

    vpc = Vpc([], [])
    mock_vpc_config_fn = Mock()
    mock_vpc_config_fn.return_value = vpc
    mock_db_connection_string_fn = Mock(return_value="test-db-connection-string")

    db_copy = DatabaseCopy(
        app,
        database,
        mocks.load_application_fn,
        mock_run_database_copy_task_fn,
        mock_db_connection_string_fn,
        mocks.input_fn,
        mocks.echo_fn,
    )
    db_copy.tail_logs = Mock()

    db_copy.load(env, vpc_name)

    mocks.environment.session_fn.assert_not_called()

    mock_vpc_config_fn.assert_not_called()

    mock_db_connection_string_fn.assert_not_called()

    mock_run_database_copy_task_fn.assert_not_called()

    mocks.input_fn.assert_called_once_with(
        f"\nAre all tasks using test-db in the test-env environment stopped? (y/n)"
    )
    mocks.echo_fn.assert_not_called()
    db_copy.tail_logs.assert_not_called()


@pytest.mark.parametrize("is_dump", (True, False))
def test_database_dump_handles_vpc_errors(is_dump):
    mocks = Mocks()

    mock_vpc_config_fn = Mock()
    mock_vpc_config_fn.side_effect = AWSException("A VPC error occurred")

    db_copy = DatabaseCopy(
        "test-app",
        "test-db",
        load_application_fn=mocks.load_application_fn,
        vpc_config_fn=mock_vpc_config_fn,
        input_fn=mocks.input_fn,
        abort_fn=mocks.abort_fn,
    )

    with pytest.raises(SystemExit) as exc:
        if is_dump:
            db_copy.dump("test-env", "bad-vpc-name")
        else:
            db_copy.load("test-env", "bad-vpc-name")

    assert exc.value.code == 1
    mocks.abort_fn.assert_called_once_with("A VPC error occurred")


@pytest.mark.parametrize("is_dump", (True, False))
def test_database_dump_handles_db_name_errors(is_dump):
    mocks = Mocks()

    mock_vpc_config_fn = Mock()
    mock_vpc_config_fn.side_effect = AWSException("A VPC error occurred")
    mock_db_connection_string_fn = Mock(side_effect=Exception("Parameter not found."))

    vpc = Vpc([], [])
    mock_vpc_config_fn = Mock()
    mock_vpc_config_fn.return_value = vpc

    db_copy = DatabaseCopy(
        "test-app",
        "bad-db",
        load_application_fn=mocks.load_application_fn,
        vpc_config_fn=mock_vpc_config_fn,
        db_connection_string_fn=mock_db_connection_string_fn,
        input_fn=mocks.input_fn,
        abort_fn=mocks.abort_fn,
    )

    with pytest.raises(SystemExit) as exc:
        if is_dump:
            db_copy.dump("test-env", "vpc-name")
        else:
            db_copy.load("test-env", "vpc-name")

    assert exc.value.code == 1
    mocks.abort_fn.assert_called_once_with(
        "Parameter not found. (Database: test-app-test-env-bad-db)"
    )


@pytest.mark.parametrize("is_dump", (True, False))
def test_database_dump_handles_env_name_errors(is_dump):
    mocks = Mocks()

    db_copy = DatabaseCopy(
        "test-app",
        "test-db",
        load_application_fn=mocks.load_application_fn,
        input_fn=mocks.input_fn,
        abort_fn=mocks.abort_fn,
    )

    with pytest.raises(SystemExit) as exc:
        if is_dump:
            db_copy.dump("bad-env", "vpc-name")
        else:
            db_copy.load("bad-env", "vpc-name")

    assert exc.value.code == 1
    mocks.abort_fn.assert_called_once_with(
        "No such environment 'bad-env'. Available environments are: test-env, test-env-2"
    )


@pytest.mark.parametrize("is_dump", (True, False))
def test_database_dump_handles_account_id_errors(is_dump):
    mocks = Mocks()
    error_msg = "An error occurred (InvalidParameterException) when calling the RunTask operation: AccountIDs mismatch"
    mock_run_database_copy_task = Mock(side_effect=Exception(error_msg))

    db_copy = DatabaseCopy(
        "test-app",
        "test-db",
        mocks.load_application_fn,
        mocks.vpc_config_fn,
        mocks.db_connection_string_fn,
        mocks.input_fn,
        mocks.echo_fn,
        mocks.abort_fn,
    )
    db_copy.run_database_copy_task = mock_run_database_copy_task

    db_copy.tail_logs = Mock()

    with pytest.raises(SystemExit) as exc:
        if is_dump:
            db_copy.dump("test-env", "vpc-name")
        else:
            db_copy.load("test-env", "vpc-name")

    assert exc.value.code == 1
    mocks.abort_fn.assert_called_once_with(f"{error_msg} (Account id: 12345)")


def test_database_copy_initializaion_handles_app_name_errors():
    mocks = Mocks()
    mocks.load_application_fn = Mock(side_effect=ApplicationNotFoundError())

    with pytest.raises(SystemExit) as exc:
        DatabaseCopy(
            "bad-app",
            "test-db",
            load_application_fn=mocks.load_application_fn,
            input_fn=mocks.input_fn,
            abort_fn=mocks.abort_fn,
        )

    assert exc.value.code == 1
    mocks.abort_fn.assert_called_once_with("No such application 'bad-app'.")


@pytest.mark.parametrize("user_response", ["y", "Y", " y ", "\ny", "YES", "yes"])
def test_is_confirmed_ready_to_load(user_response):
    mock_input = Mock()
    mock_input.return_value = user_response
    db_copy = DatabaseCopy(
        "",
        "test-db",
        Mock(),
        None,
        None,
        mock_input,
    )

    assert db_copy.is_confirmed_ready_to_load("test-env")

    mock_input.assert_called_once_with(
        f"\nAre all tasks using test-db in the test-env environment stopped? (y/n)"
    )


@pytest.mark.parametrize("user_response", ["n", "N", " no ", "squiggly"])
def test_is_not_confirmed_ready_to_load(user_response):
    mock_input = Mock()
    mock_input.return_value = user_response
    db_copy = DatabaseCopy(
        None,
        "test-db",
        Mock(),
        None,
        None,
        mock_input,
    )

    assert not db_copy.is_confirmed_ready_to_load("test-env")

    mock_input.assert_called_once_with(
        f"\nAre all tasks using test-db in the test-env environment stopped? (y/n)"
    )


@pytest.mark.parametrize("is_dump", [True, False])
def test_tail_logs(is_dump):
    action = "dump" if is_dump else "load"

    mocks = Mocks()

    mocks.client.start_live_tail.return_value = {
        "responseStream": [
            {"sessionStart": {}},
            {"sessionUpdate": {"sessionResults": []}},
            {"sessionUpdate": {"sessionResults": [{"message": ""}]}},
            {"sessionUpdate": {"sessionResults": [{"message": f"Starting data {action}"}]}},
            {"sessionUpdate": {"sessionResults": [{"message": "A load of SQL shenanigans"}]}},
            {"sessionUpdate": {"sessionResults": [{"message": f"Stopping data {action}"}]}},
        ]
    }

    db_copy = DatabaseCopy(
        "test-app",
        "test-db",
        mocks.load_application_fn,
        None,
        None,
        mocks.input_fn,
        echo_fn=mocks.echo_fn,
    )
    db_copy.tail_logs(is_dump, "test-env")

    mocks.environment.session.client.assert_called_once_with("logs")
    mocks.client.start_live_tail.assert_called_once_with(
        logGroupIdentifiers=[
            f"arn:aws:logs:eu-west-2:12345:log-group:/ecs/test-app-test-env-test-db-{action}"
        ],
    )

    mocks.echo_fn.assert_has_calls(
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


def test_database_copy_account_id():
    mocks = Mocks()

    db_copy = DatabaseCopy(
        "test-app",
        "test-db",
        mocks.load_application_fn,
    )

    assert db_copy.account_id("test-env") == "12345"
