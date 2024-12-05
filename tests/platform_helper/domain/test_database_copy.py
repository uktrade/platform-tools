from unittest.mock import Mock
from unittest.mock import call

import pytest
import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.domain.database_copy import DatabaseCopy
from dbt_platform_helper.providers.aws import AWSException
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import ApplicationNotFoundError
from dbt_platform_helper.utils.aws import Vpc


class DataCopyMocks:
    def __init__(self, app="test-app", env="test-env", acc="12345", vpc=Vpc([], [])):
        self.application = Application(app)
        self.environment = Mock()
        self.environment.account_id = acc
        self.application.environments = {env: self.environment, "test-env-2": Mock()}
        self.load_application = Mock(return_value=self.application)
        self.client = Mock()
        self.environment.session.client.return_value = self.client

        self.vpc = vpc
        self.vpc_config = Mock()
        self.vpc_config.return_value = vpc
        self.db_connection_string = Mock(return_value="test-db-connection-string")
        self.maintenance_page_provider = Mock()

        self.input = Mock(return_value="yes")
        self.echo = Mock()
        self.abort = Mock(side_effect=SystemExit(1))

    def params(self):
        return {
            "load_application": self.load_application,
            "vpc_config": self.vpc_config,
            "db_connection_string": self.db_connection_string,
            "maintenance_page_provider": self.maintenance_page_provider,
            "input": self.input,
            "echo": self.echo,
            "abort": self.abort,
        }


@pytest.mark.parametrize("is_dump, exp_operation", [(True, "dump"), (False, "load")])
def test_run_database_copy_task(is_dump, exp_operation):
    vpc = Vpc(["subnet_1", "subnet_2"], ["sec_group_1"])
    mocks = DataCopyMocks(vpc=vpc)
    db_connection_string = "connection_string"

    db_copy = DatabaseCopy("test-app", "test-postgres", **mocks.params())

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.run_task.return_value = {"tasks": [{"taskArn": "arn:aws:ecs:test-task-arn"}]}

    actual_task_arn = db_copy.run_database_copy_task(
        mock_session, "test-env", vpc, is_dump, db_connection_string, "test-env"
    )

    assert actual_task_arn == "arn:aws:ecs:test-task-arn"

    mock_session.client.assert_called_once_with("ecs")
    expected_env_vars = [
        {"name": "DATA_COPY_OPERATION", "value": exp_operation.upper()},
        {"name": "DB_CONNECTION_STRING", "value": "connection_string"},
        {"name": "TO_ENVIRONMENT", "value": "test-env"},
    ]
    if not is_dump:
        expected_env_vars.append(
            {"name": "ECS_CLUSTER", "value": "test-app-test-env"},
        )

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
                    "environment": expected_env_vars,
                }
            ]
        },
    )


def test_database_dump():
    app = "test-app"
    env = "test-env"
    vpc_name = "test-vpc"
    database = "test-db"

    mocks = DataCopyMocks(app, env)

    mock_run_database_copy_task = Mock(return_value="arn://task-arn")

    db_copy = DatabaseCopy(app, database, **mocks.params())
    db_copy.run_database_copy_task = mock_run_database_copy_task

    db_copy.tail_logs = Mock()
    db_copy.enrich_vpc_name = Mock()
    db_copy.enrich_vpc_name.return_value = "test-vpc-override"

    db_copy.dump(env, vpc_name, "test-env")

    mocks.load_application.assert_called_once()
    mocks.vpc_config.assert_called_once_with(
        mocks.environment.session, app, env, "test-vpc-override"
    )
    mocks.db_connection_string.assert_called_once_with(
        mocks.environment.session, app, env, "test-app-test-env-test-db"
    )
    mock_run_database_copy_task.assert_called_once_with(
        mocks.environment.session, env, mocks.vpc, True, "test-db-connection-string", "test-env"
    )
    mocks.input.assert_not_called()
    mocks.echo.assert_has_calls(
        [
            call("Dumping test-db from the test-env environment into S3", fg="white", bold=True),
            call(
                "Task arn://task-arn started. Waiting for it to complete (this may take some time)...",
                fg="white",
            ),
        ]
    )
    db_copy.tail_logs.assert_called_once_with(True, env)
    db_copy.enrich_vpc_name.assert_called_once_with("test-env", "test-vpc")


def test_database_load_with_response_of_yes():
    app = "test-app"
    env = "test-env"
    vpc_name = "test-vpc"
    mocks = DataCopyMocks()

    mock_run_database_copy_task = Mock(return_value="arn://task-arn")

    db_copy = DatabaseCopy(app, "test-db", **mocks.params())
    db_copy.tail_logs = Mock()
    db_copy.enrich_vpc_name = Mock()
    db_copy.enrich_vpc_name.return_value = "test-vpc-override"
    db_copy.run_database_copy_task = mock_run_database_copy_task

    db_copy.load(env, vpc_name)

    mocks.load_application.assert_called_once()

    mocks.vpc_config.assert_called_once_with(
        mocks.environment.session, app, env, "test-vpc-override"
    )

    mocks.db_connection_string.assert_called_once_with(
        mocks.environment.session, app, env, "test-app-test-env-test-db"
    )

    mock_run_database_copy_task.assert_called_once_with(
        mocks.environment.session, env, mocks.vpc, False, "test-db-connection-string", "test-env"
    )

    mocks.input.assert_called_once_with(
        f"\nWARNING: the load operation is destructive and will delete the test-db database in the test-env environment. Continue? (y/n)"
    )

    mocks.echo.assert_has_calls(
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
    db_copy.enrich_vpc_name.assert_called_once_with("test-env", "test-vpc")


def test_database_load_with_response_of_no():
    mocks = DataCopyMocks()
    mocks.input = Mock(return_value="no")

    mock_run_database_copy_task = Mock()

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())
    db_copy.tail_logs = Mock()
    db_copy.run_database_copy_task = mock_run_database_copy_task

    db_copy.load("test-env", "test-vpc")

    mocks.environment.session.assert_not_called()

    mocks.vpc_config.assert_not_called()

    mocks.db_connection_string.assert_not_called()

    mock_run_database_copy_task.assert_not_called()

    mocks.input.assert_called_once_with(
        f"\nWARNING: the load operation is destructive and will delete the test-db database in the test-env environment. Continue? (y/n)"
    )
    mocks.echo.assert_not_called()
    db_copy.tail_logs.assert_not_called()


@pytest.mark.parametrize("is_dump", (True, False))
def test_database_dump_handles_vpc_errors(is_dump):
    mocks = DataCopyMocks()
    mocks.vpc_config.side_effect = AWSException("A VPC error occurred")

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    with pytest.raises(SystemExit) as exc:
        if is_dump:
            db_copy.dump("test-env", "bad-vpc-name", "test-env")
        else:
            db_copy.load("test-env", "bad-vpc-name")

    assert exc.value.code == 1
    mocks.abort.assert_called_once_with("A VPC error occurred")


@pytest.mark.parametrize("is_dump", (True, False))
def test_database_dump_handles_db_name_errors(is_dump):
    mocks = DataCopyMocks()
    mocks.db_connection_string = Mock(side_effect=Exception("Parameter not found."))

    db_copy = DatabaseCopy("test-app", "bad-db", **mocks.params())

    with pytest.raises(SystemExit) as exc:
        if is_dump:
            db_copy.dump("test-env", "vpc-name", "test-env")
        else:
            db_copy.load("test-env", "vpc-name")

    assert exc.value.code == 1
    mocks.abort.assert_called_once_with("Parameter not found. (Database: test-app-test-env-bad-db)")


@pytest.mark.parametrize("is_dump", (True, False))
def test_database_dump_handles_env_name_errors(is_dump):
    mocks = DataCopyMocks()

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    with pytest.raises(SystemExit) as exc:
        if is_dump:
            db_copy.dump("bad-env", "vpc-name", "test-env")
        else:
            db_copy.load("bad-env", "vpc-name")

    assert exc.value.code == 1
    mocks.abort.assert_called_once_with(
        "No such environment 'bad-env'. Available environments are: test-env, test-env-2"
    )


@pytest.mark.parametrize("is_dump", (True, False))
def test_database_dump_handles_account_id_errors(is_dump):
    mocks = DataCopyMocks()
    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())
    error_msg = "An error occurred (InvalidParameterException) when calling the RunTask operation: AccountIDs mismatch"
    db_copy.run_database_copy_task = Mock(side_effect=Exception(error_msg))

    db_copy.tail_logs = Mock()

    with pytest.raises(SystemExit) as exc:
        if is_dump:
            db_copy.dump("test-env", "vpc-name", "test-env")
        else:
            db_copy.load("test-env", "vpc-name")

    assert exc.value.code == 1
    mocks.abort.assert_called_once_with(f"{error_msg} (Account id: 12345)")


def test_database_copy_initialization_handles_app_name_errors():
    mocks = DataCopyMocks()
    mocks.load_application = Mock(side_effect=ApplicationNotFoundError("bad-app"))

    with pytest.raises(SystemExit) as exc:
        DatabaseCopy("bad-app", "test-db", **mocks.params())

    assert exc.value.code == 1
    mocks.abort.assert_called_once_with("No such application 'bad-app'.")


@pytest.mark.parametrize("user_response", ["y", "Y", " y ", "\ny", "YES", "yes"])
def test_is_confirmed_ready_to_load(user_response):
    mocks = DataCopyMocks()
    mocks.input.return_value = user_response

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    assert db_copy.is_confirmed_ready_to_load("test-env")

    mocks.input.assert_called_once_with(
        f"\nWARNING: the load operation is destructive and will delete the test-db database in the test-env environment. Continue? (y/n)"
    )


@pytest.mark.parametrize("user_response", ["n", "N", " no ", "squiggly"])
def test_is_not_confirmed_ready_to_load(user_response):
    mocks = DataCopyMocks()
    mocks.input.return_value = user_response

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    assert not db_copy.is_confirmed_ready_to_load("test-env")

    mocks.input.assert_called_once_with(
        f"\nWARNING: the load operation is destructive and will delete the test-db database in the test-env environment. Continue? (y/n)"
    )


def test_is_confirmed_ready_to_load_with_yes_flag():
    mocks = DataCopyMocks()

    db_copy = DatabaseCopy("test-app", "test-db", True, **mocks.params())

    assert db_copy.is_confirmed_ready_to_load("test-env")

    mocks.input.assert_not_called()


@pytest.mark.parametrize(
    "services, template",
    (
        (["web"], "default"),
        (["*"], "default"),
        (["web", "other"], "migrations"),
    ),
)
def test_copy_command(services, template):
    mocks = DataCopyMocks()
    db_copy = DatabaseCopy("test-app", "test-db", True, **mocks.params())
    db_copy.dump = Mock()
    db_copy.load = Mock()
    db_copy.enrich_vpc_name = Mock()
    db_copy.enrich_vpc_name.return_value = "test-vpc-override"

    db_copy.copy("test-from-env", "test-to-env", "test-from-vpc", "test-to-vpc", services, template)

    db_copy.enrich_vpc_name.assert_called_once_with("test-to-env", "test-to-vpc")
    mocks.maintenance_page_provider.activate.assert_called_once_with(
        "test-app", "test-to-env", services, template, "test-vpc-override"
    )
    db_copy.dump.assert_called_once_with("test-from-env", "test-from-vpc", "test-to-env")
    db_copy.load.assert_called_once_with("test-to-env", "test-vpc-override")
    mocks.maintenance_page_provider.deactivate.assert_called_once_with("test-app", "test-to-env")


@pytest.mark.parametrize(
    "services, template",
    (
        (["web"], "default"),
        (["*"], "default"),
        (["web", "other"], "migrations"),
    ),
)
def test_copy_command_with_no_maintenance_page(services, template):
    mocks = DataCopyMocks()
    db_copy = DatabaseCopy("test-app", "test-db", True, **mocks.params())
    db_copy.dump = Mock()
    db_copy.load = Mock()
    db_copy.enrich_vpc_name = Mock()
    db_copy.enrich_vpc_name.return_value = "test-vpc-override"

    db_copy.copy(
        "test-from-env", "test-to-env", "test-from-vpc", "test-to-vpc", services, template, True
    )

    mocks.maintenance_page_provider.offline.assert_not_called()
    mocks.maintenance_page_provider.online.assert_not_called()


@pytest.mark.parametrize("is_dump", [True, False])
def test_tail_logs(is_dump):
    action = "dump" if is_dump else "load"

    mocks = DataCopyMocks()

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

    mocks.client.describe_log_groups.return_value = {
        "logGroups": [{"logGroupName": f"/ecs/test-app-test-env-test-db-{action}"}]
    }

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())
    db_copy.tail_logs(is_dump, "test-env")

    mocks.environment.session.client.assert_called_once_with("logs")
    mocks.client.start_live_tail.assert_called_once_with(
        logGroupIdentifiers=[
            f"arn:aws:logs:eu-west-2:12345:log-group:/ecs/test-app-test-env-test-db-{action}"
        ],
    )

    mocks.echo.assert_has_calls(
        [
            call(
                f"Tailing /ecs/test-app-test-env-test-db-{action} logs",
                fg="yellow",
            ),
            call(f"Starting data {action}"),
            call("A load of SQL shenanigans"),
            call(f"Stopping data {action}"),
        ]
    )


@pytest.mark.parametrize("is_dump", [True, False])
def test_tail_logs_exits_with_error_if_task_aborts(is_dump):
    action = "dump" if is_dump else "load"

    mocks = DataCopyMocks()

    mocks.client.start_live_tail.return_value = {
        "responseStream": [
            {"sessionStart": {}},
            {"sessionUpdate": {"sessionResults": []}},
            {"sessionUpdate": {"sessionResults": [{"message": ""}]}},
            {"sessionUpdate": {"sessionResults": [{"message": f"Starting data {action}"}]}},
            {"sessionUpdate": {"sessionResults": [{"message": "A load of SQL shenanigans"}]}},
            {"sessionUpdate": {"sessionResults": [{"message": f"Aborting data {action}"}]}},
        ]
    }

    mocks.client.describe_log_groups.return_value = {
        "logGroups": [{"logGroupName": f"/ecs/test-app-test-env-test-db-{action}"}]
    }

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    with pytest.raises(SystemExit) as exc:
        db_copy.tail_logs(is_dump, "test-env")

    assert exc.value.code == 1
    mocks.abort.assert_called_once_with("Task aborted abnormally. See logs above for details.")


def test_database_copy_account_id():
    mocks = DataCopyMocks()

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    assert db_copy.account_id("test-env") == "12345"


def test_update_application_from_platform_config_if_application_not_specified(fs):
    fs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump({"application": "test-app"}))
    mocks = DataCopyMocks()

    db_copy = DatabaseCopy(None, "test-db", **mocks.params())

    assert db_copy.app == "test-app"


def test_error_if_neither_platform_config_or_application_supplied(fs):
    # fakefs used here to ensure the platform-config.yml isn't picked up from the filesystem
    mocks = DataCopyMocks()

    with pytest.raises(SystemExit) as exc:
        DatabaseCopy(None, "test-db", **mocks.params())

    assert exc.value.code == 1
    mocks.abort.assert_called_once_with(
        "You must either be in a deploy repo, or provide the --app option."
    )


@pytest.mark.parametrize("is_dump", [True, False])
def test_database_dump_with_no_vpc_works_in_deploy_repo(fs, is_dump):
    fs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(
            {"application": "test-app", "environments": {"test-env": {"vpc": "test-env-vpc"}}}
        ),
    )
    env = "test-env"
    database = "test-db"

    mocks = DataCopyMocks()

    mock_run_database_copy_task = Mock(return_value="arn://task-arn")

    db_copy = DatabaseCopy(None, database, **mocks.params())

    db_copy.run_database_copy_task = mock_run_database_copy_task
    db_copy.tail_logs = Mock()

    if is_dump:
        db_copy.dump(env, None, "test-env")
    else:
        db_copy.load(env, None)

    mocks.vpc_config.assert_called_once_with(
        mocks.environment.session, "test-app", env, "test-env-vpc"
    )


@pytest.mark.parametrize("is_dump", [True, False])
def test_database_dump_with_no_vpc_fails_if_not_in_deploy_repo(fs, is_dump):
    # fakefs used here to ensure the platform-config.yml isn't picked up from the filesystem
    env = "test-env"
    database = "test-db"

    mocks = DataCopyMocks()

    mock_run_database_copy_task = Mock(return_value="arn://task-arn")

    db_copy = DatabaseCopy("test-app", database, **mocks.params())

    db_copy.run_database_copy_task = mock_run_database_copy_task
    db_copy.tail_logs = Mock()

    with pytest.raises(SystemExit) as exc:
        if is_dump:
            db_copy.dump(env, None, "test-env")
        else:
            db_copy.load(env, None)

    assert exc.value.code == 1
    mocks.abort.assert_called_once_with(
        f"You must either be in a deploy repo, or provide the vpc name option."
    )


def test_enrich_vpc_name_returns_the_vpc_name_passed_in():
    db_copy = DatabaseCopy("test-app", "test-db", **DataCopyMocks().params())
    vpc_name = db_copy.enrich_vpc_name("test-env", "test-vpc")

    assert vpc_name == "test-vpc"


def test_enrich_vpc_name_aborts_if_no_platform_config(fs):
    # fakefs used here to ensure the platform-config.yml isn't picked up from the filesystem
    mocks = DataCopyMocks()
    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    with pytest.raises(SystemExit):
        db_copy.enrich_vpc_name("test-env", None)

    mocks.abort.assert_called_once_with(
        f"You must either be in a deploy repo, or provide the vpc name option."
    )


def test_enrich_vpc_name_enriches_vpc_name_from_platform_config(fs):
    # fakefs used here to ensure the platform-config.yml isn't picked up from the filesystem
    fs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(
            {"application": "test-app", "environments": {"test-env": {"vpc": "test-env-vpc"}}}
        ),
    )
    mocks = DataCopyMocks()
    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    vpc_name = db_copy.enrich_vpc_name("test-env", None)

    assert vpc_name == "test-env-vpc"


def test_enrich_vpc_name_enriches_vpc_name_from_environment_defaults(fs):
    # fakefs used here to ensure the platform-config.yml isn't picked up from the filesystem
    fs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(
            {
                "application": "test-app",
                "environments": {"*": {"vpc": "test-env-vpc"}, "test-env": {}},
            }
        ),
    )
    mocks = DataCopyMocks()
    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    vpc_name = db_copy.enrich_vpc_name("test-env", None)

    assert vpc_name == "test-env-vpc"
