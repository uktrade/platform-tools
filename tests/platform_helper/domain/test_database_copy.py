from unittest.mock import Mock
from unittest.mock import call

import pytest
import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_CONFIG_SCHEMA_VERSION
from dbt_platform_helper.domain.database_copy import DatabaseCopy
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.vpc import Vpc
from dbt_platform_helper.providers.vpc import VpcProviderException
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import ApplicationNotFoundException


class DataCopyMocks:
    def __init__(
        self,
        app="test-app",
        env="test-env",
        acc="12345",
        vpc=Vpc("", [], ["subnet_1", "subnet_2"], ["sec_group_1"]),
        **kwargs,
    ):
        self.application = Application(app)
        self.environment = Mock()
        self.environment.account_id = acc
        self.application.environments = {env: self.environment, "test-env-2": Mock()}
        self.load_application = Mock(return_value=self.application)
        self.client = Mock()
        self.environment.session.client.return_value = self.client

        self.vpc = vpc
        self.vpc_provider = (
            Mock()
        )  # this is the callable class so should return a class when called
        self.instantiated_vpc_provider = Mock()
        self.instantiated_vpc_provider.get_vpc.return_value = self.vpc
        self.vpc_provider.return_value = self.instantiated_vpc_provider
        self.db_connection_string = Mock(return_value="test-db-connection-string")
        self.maintenance_page_instance = Mock()
        self.maintenance_page_instance.activate.return_value = None
        self.maintenance_page_instance.deactivate.return_value = None
        self.maintenance_page = Mock(return_value=self.maintenance_page_instance)

        self.io = Mock()
        self.io.confirm = Mock(return_value="yes")
        self.io.abort_with_error = Mock(side_effect=SystemExit(1))

        self.config_provider = kwargs.get("config_provider", Mock())

    def params(self):
        return {
            "load_application": self.load_application,
            "vpc_provider": self.vpc_provider,
            "db_connection_string": self.db_connection_string,
            "maintenance_page": self.maintenance_page,
            "io": self.io,
            "config_provider": self.config_provider,
        }


@pytest.mark.parametrize("is_dump, exp_operation", [(True, "dump"), (False, "load")])
def test_run_database_copy_task(is_dump, exp_operation):
    mocks = DataCopyMocks()
    db_connection_string = "connection_string"

    db_copy = DatabaseCopy("test-app", "test-postgres", **mocks.params())

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.run_task.return_value = {"tasks": [{"taskArn": "arn:aws:ecs:test-task-arn"}]}

    actual_task_arn = db_copy.run_database_copy_task(
        mock_session, "test-env", mocks.vpc, is_dump, db_connection_string, "test-dump-file"
    )

    assert actual_task_arn == "arn:aws:ecs:test-task-arn"

    mock_session.client.assert_called_once_with("ecs")
    expected_env_vars = [
        {"name": "DATA_COPY_OPERATION", "value": exp_operation.upper()},
        {"name": "DB_CONNECTION_STRING", "value": "connection_string"},
        {"name": "DUMP_FILE_NAME", "value": "test-dump-file"},
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

    db_copy.dump(env, vpc_name)

    mocks.load_application.assert_called_once()
    mocks.vpc_provider.assert_called_once_with(mocks.environment.session)
    mocks.instantiated_vpc_provider.get_vpc.assert_called_once_with(app, env, "test-vpc-override")
    mocks.db_connection_string.assert_called_once_with(
        mocks.environment.session, app, env, "test-app-test-env-test-db"
    )
    mock_run_database_copy_task.assert_called_once_with(
        mocks.environment.session, env, mocks.vpc, True, "test-db-connection-string", None
    )
    mocks.io.confirm.assert_not_called()
    mocks.io.info.assert_has_calls(
        [
            call("Dumping test-db from the test-env environment into S3"),
            call(
                "Task arn://task-arn started. Waiting for it to complete (this may take some time)...",
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

    mocks.vpc_provider.assert_called_once_with(mocks.environment.session)
    mocks.instantiated_vpc_provider.get_vpc.assert_called_once_with(app, env, "test-vpc-override")

    mocks.db_connection_string.assert_called_once_with(
        mocks.environment.session, app, env, "test-app-test-env-test-db"
    )

    mock_run_database_copy_task.assert_called_once_with(
        mocks.environment.session, env, mocks.vpc, False, "test-db-connection-string", None
    )

    mocks.io.confirm.assert_called_once_with(
        f"\nWARNING: the load operation is destructive and will delete the test-db database in the test-env environment. Continue?"
    )

    mocks.io.info.assert_has_calls(
        [
            call(
                "Loading data into test-db in the test-env environment from S3",
            ),
            call(
                "Task arn://task-arn started. Waiting for it to complete (this may take some time)...",
            ),
        ]
    )
    db_copy.tail_logs.assert_called_once_with(False, "test-env")
    db_copy.enrich_vpc_name.assert_called_once_with("test-env", "test-vpc")


def test_database_load_with_response_of_no():
    mocks = DataCopyMocks()
    mocks.io.confirm.return_value = False

    mock_run_database_copy_task = Mock()

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())
    db_copy.tail_logs = Mock()
    db_copy.run_database_copy_task = mock_run_database_copy_task

    db_copy.load("test-env", "test-vpc")

    mocks.environment.session.assert_not_called()

    mocks.vpc_provider.assert_not_called()
    mocks.instantiated_vpc_provider.get_vpc.assert_not_called()

    mocks.db_connection_string.assert_not_called()

    mock_run_database_copy_task.assert_not_called()

    mocks.io.confirm.assert_called_once_with(
        f"\nWARNING: the load operation is destructive and will delete the test-db database in the test-env environment. Continue?"
    )
    mocks.io.info.assert_not_called()
    db_copy.tail_logs.assert_not_called()


@pytest.mark.parametrize("is_dump", (True, False))
def test_database_dump_handles_vpc_errors(is_dump):
    mocks = DataCopyMocks()
    mocks.instantiated_vpc_provider.get_vpc.side_effect = VpcProviderException(
        "A VPC error occurred"
    )

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    with pytest.raises(SystemExit) as exc:
        if is_dump:
            db_copy.dump("test-env", "bad-vpc-name", "test-env")
        else:
            db_copy.load("test-env", "bad-vpc-name")

    assert exc.value.code == 1
    mocks.vpc_provider.assert_called_once_with(mocks.environment.session)
    mocks.io.abort_with_error.assert_called_once_with("A VPC error occurred")


@pytest.mark.parametrize("is_dump", (True, False))
def test_database_dump_handles_db_name_errors(is_dump):
    mocks = DataCopyMocks()
    mocks.db_connection_string = Mock(side_effect=Exception("Parameter not found."))

    db_copy = DatabaseCopy("test-app", "bad-db", **mocks.params())

    with pytest.raises(SystemExit) as exc:
        if is_dump:
            db_copy.dump("test-env", "vpc-name")
        else:
            db_copy.load("test-env", "vpc-name")

    assert exc.value.code == 1
    mocks.io.abort_with_error.assert_called_once_with(
        "Parameter not found. (Database: test-app-test-env-bad-db)"
    )


@pytest.mark.parametrize("is_dump", (True, False))
def test_database_dump_handles_env_name_errors(is_dump):
    mocks = DataCopyMocks()

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    with pytest.raises(SystemExit) as exc:
        if is_dump:
            db_copy.dump("bad-env", "vpc-name")
        else:
            db_copy.load("bad-env", "vpc-name")

    assert exc.value.code == 1
    mocks.io.abort_with_error.assert_called_once_with(
        "No such environment 'bad-env'. Available environments are: test-env, test-env-2"
    )


@pytest.mark.parametrize("is_dump", (True, False))
def test_database_dump_handles_missing_security_groups(is_dump):
    vpc = Vpc("123", ["public_subnet"], ["private_subnet"], [])
    mocks = DataCopyMocks(vpc=vpc)

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    with pytest.raises(SystemExit) as exc:
        if is_dump:
            db_copy.dump("test-env", "vpc-name")
        else:
            db_copy.load("test-env", "vpc-name")

    assert exc.value.code == 1
    mocks.io.abort_with_error.assert_called_once_with("No security groups found in vpc 'vpc-name'")


@pytest.mark.parametrize("is_dump", (True, False))
def test_database_dump_handles_account_id_errors(is_dump):
    mocks = DataCopyMocks()
    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())
    error_msg = "An error occurred (InvalidParameterException) when calling the RunTask operation: AccountIDs mismatch"
    db_copy.run_database_copy_task = Mock(side_effect=Exception(error_msg))

    db_copy.tail_logs = Mock()

    with pytest.raises(SystemExit) as exc:
        if is_dump:
            db_copy.dump("test-env", "vpc-name")
        else:
            db_copy.load("test-env", "vpc-name")

    assert exc.value.code == 1
    mocks.io.abort_with_error.assert_called_once_with(f"{error_msg} (Account id: 12345)")


def test_database_copy_initialization_handles_app_name_errors():
    mocks = DataCopyMocks()
    mocks.load_application = Mock(side_effect=ApplicationNotFoundException("bad-app"))

    with pytest.raises(SystemExit) as exc:
        DatabaseCopy("bad-app", "test-db", **mocks.params())

    assert exc.value.code == 1
    mocks.io.abort_with_error.assert_called_once_with("No such application 'bad-app'.")


@pytest.mark.parametrize("user_response", ["y", "Y", " y ", "\ny", "YES", "yes"])
def test_is_confirmed_ready_to_load(user_response):
    mocks = DataCopyMocks()
    mocks.io.confirm.return_value = user_response

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    assert db_copy.is_confirmed_ready_to_load("test-env")

    mocks.io.confirm.assert_called_once_with(
        f"\nWARNING: the load operation is destructive and will delete the test-db database in the test-env environment. Continue?"
    )


def test_is_not_confirmed_ready_to_load():
    mocks = DataCopyMocks()
    mocks.io.confirm.return_value = False

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    assert not db_copy.is_confirmed_ready_to_load("test-env")

    mocks.io.confirm.assert_called_once_with(
        f"\nWARNING: the load operation is destructive and will delete the test-db database in the test-env environment. Continue?"
    )


def test_is_not_confirmed_if_invalid_user_input_type():
    mocks = DataCopyMocks()
    mocks.io.confirm.return_value = False

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    assert not db_copy.is_confirmed_ready_to_load("test-env")

    mocks.io.confirm.assert_called_once_with(
        f"\nWARNING: the load operation is destructive and will delete the test-db database in the test-env environment. Continue?"
    )


def test_is_confirmed_ready_to_load_with_yes_flag():
    mocks = DataCopyMocks()

    db_copy = DatabaseCopy("test-app", "test-db", True, **mocks.params())

    assert db_copy.is_confirmed_ready_to_load("test-env")

    mocks.io.confirm.assert_not_called()


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
    mocks.maintenance_page.assert_called_once_with(mocks.application)
    mocks.maintenance_page_instance.activate.assert_called_once_with(
        "test-to-env", services, template, "test-vpc-override"
    )
    db_copy.dump.assert_called_once_with("test-from-env", "test-from-vpc", "data_dump_test-to-env")
    db_copy.load.assert_called_once_with(
        "test-to-env", "test-vpc-override", "data_dump_test-to-env"
    )

    mocks.maintenance_page_instance.deactivate.assert_called_once_with("test-to-env")


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

    mocks.maintenance_page.offline.assert_not_called()
    mocks.maintenance_page.online.assert_not_called()


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

    mocks.io.warn.assert_has_calls(
        [
            call(
                f"Tailing /ecs/test-app-test-env-test-db-{action} logs",
            )
        ]
    )
    mocks.io.info.assert_has_calls(
        [
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
    mocks.io.abort_with_error.assert_called_once_with(
        "Task aborted abnormally. See logs above for details."
    )


def test_database_copy_account_id():
    mocks = DataCopyMocks()

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    assert db_copy.account_id("test-env") == "12345"


def test_update_application_from_platform_config_if_application_not_specified(fs):
    fs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(
            {
                "schema_version": PLATFORM_CONFIG_SCHEMA_VERSION,
                "default_versions": {"platform-helper": "14.0.0"},
                "application": "test-app",
            }
        ),
    )

    config_validator = Mock()
    config_validator.run_validations.return_value = None
    config_provider = ConfigProvider(config_validator, installed_platform_helper_version="14.0.0")

    mocks = DataCopyMocks(config_provider=config_provider)

    db_copy = DatabaseCopy(None, "test-db", **mocks.params())

    assert db_copy.app == "test-app"


def test_error_if_neither_platform_config_or_application_supplied(fs):
    # fakefs used here to ensure the platform-config.yml isn't picked up from the filesystem
    mocks = DataCopyMocks()

    with pytest.raises(SystemExit) as exc:
        DatabaseCopy(None, "test-db", **mocks.params())

    assert exc.value.code == 1
    mocks.io.abort_with_error.assert_called_once_with(
        "You must either be in a deploy repo, or provide the --app option."
    )


@pytest.mark.parametrize("is_dump", [True, False])
def test_database_dump_with_no_vpc_works_in_deploy_repo(fs, is_dump):
    fs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(
            {
                "schema_version": PLATFORM_CONFIG_SCHEMA_VERSION,
                "default_versions": {"platform-helper": "14.0.0"},
                "application": "test-app",
                "environments": {"test-env": {"vpc": "test-env-vpc"}},
            }
        ),
    )
    env = "test-env"
    database = "test-db"

    config_validator = Mock()
    config_validator.run_validations.return_value = None
    config_provider = ConfigProvider(config_validator, installed_platform_helper_version="14.0.0")

    mocks = DataCopyMocks(config_provider=config_provider)

    mock_run_database_copy_task = Mock(return_value="arn://task-arn")

    db_copy = DatabaseCopy(None, database, **mocks.params())

    db_copy.run_database_copy_task = mock_run_database_copy_task
    db_copy.tail_logs = Mock()

    if is_dump:
        db_copy.dump(env, None, "test-env")
    else:
        db_copy.load(env, None)

    mocks.vpc_provider.assert_called_once_with(mocks.environment.session)
    mocks.instantiated_vpc_provider.get_vpc.assert_called_once_with("test-app", env, "test-env-vpc")


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
    mocks.io.abort_with_error.assert_called_once_with(
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

    mocks.io.abort_with_error.assert_called_once_with(
        f"You must either be in a deploy repo, or provide the vpc name option."
    )


def test_enrich_vpc_name_enriches_vpc_name_from_platform_config(fs):
    # fakefs used here to ensure the platform-config.yml isn't picked up from the filesystem
    fs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(
            {
                "schema_version": PLATFORM_CONFIG_SCHEMA_VERSION,
                "default_versions": {"platform-helper": "14.0.0"},
                "application": "test-app",
                "environments": {"test-env": {"vpc": "test-env-vpc"}},
            }
        ),
    )
    config_validator = Mock()
    config_validator.run_validations.return_value = None
    config_provider = ConfigProvider(config_validator, installed_platform_helper_version="14.0.0")

    mocks = DataCopyMocks(config_provider=config_provider)

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    vpc_name = db_copy.enrich_vpc_name("test-env", None)

    assert vpc_name == "test-env-vpc"


def test_enrich_vpc_name_enriches_vpc_name_from_environment_defaults(fs):
    # fakefs used here to ensure the platform-config.yml isn't picked up from the filesystem
    fs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(
            {
                "schema_version": PLATFORM_CONFIG_SCHEMA_VERSION,
                "default_versions": {"platform-helper": "14.0.0"},
                "application": "test-app",
                "environments": {"*": {"vpc": "test-env-vpc"}, "test-env": {}},
            }
        ),
    )

    config_validator = Mock()
    config_validator.run_validations.return_value = None
    config_provider = ConfigProvider(config_validator, installed_platform_helper_version="14.0.0")

    mocks = DataCopyMocks(config_provider=config_provider)

    db_copy = DatabaseCopy("test-app", "test-db", **mocks.params())

    vpc_name = db_copy.enrich_vpc_name("test-env", None)

    assert vpc_name == "test-env-vpc"
