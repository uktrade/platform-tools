from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import call

import pytest

from dbt_platform_helper.domain.conduit import Conduit
from dbt_platform_helper.providers.aws.exceptions import CreateTaskTimeoutException
from dbt_platform_helper.providers.ecs import ECSAgentNotRunningException
from dbt_platform_helper.providers.ecs import NoClusterException
from dbt_platform_helper.providers.secrets import AddonNotFoundException
from dbt_platform_helper.providers.secrets import InvalidAddonTypeException
from dbt_platform_helper.providers.secrets import ParameterNotFoundException
from dbt_platform_helper.providers.secrets import SecretNotFoundException
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import Environment


class TestConduitTerraform:

    def setup(self, app_name="test-application", *args, **kwargs):

        self.secrets_provider = MagicMock()
        self.cloudformation_provider = MagicMock()
        self.ecs_provider = MagicMock()
        self.io = MagicMock()
        self.strategy_factory = MagicMock()
        self.vpc_provider = MagicMock()

        self.ecs_client = MagicMock()
        self.iam_client = MagicMock()
        self.ssm_client = MagicMock()

        self.session = MagicMock()
        self.session.client.side_effect = lambda service: {
            "ecs": self.ecs_client,
            "iam": self.iam_client,
            "ssm": self.ssm_client,
        }.get(service)

        env = "development"
        sessions = {"000000000": self.session}
        dummy_application = Application(app_name)
        dummy_application.environments = {env: Environment(env, "000000000", sessions)}
        self.application = dummy_application

        self.conduit = Conduit(
            self.application,
            self.secrets_provider,
            self.cloudformation_provider,
            self.ecs_provider,
            self.io,
            self.vpc_provider,
            self.strategy_factory,
        )

    @pytest.mark.parametrize(
        "mode, addon_type, addon_name, access, info_message",
        [
            (
                "copilot",
                "postgres",
                "custom-name-postgres",
                "read",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-postgres\n  Addon Type : postgres\n  Access Level : read",
            ),
            (
                "copilot",
                "postgres",
                "custom-name-postgres",
                "write",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-postgres\n  Addon Type : postgres\n  Access Level : write",
            ),
            (
                "copilot",
                "postgres",
                "custom-name-postgres",
                "admin",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-postgres\n  Addon Type : postgres\n  Access Level : admin",
            ),
            (
                "copilot",
                "opensearch",
                "custom-name-opensearch",
                "read",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-opensearch\n  Addon Type : opensearch",
            ),
            (
                "copilot",
                "redis",
                "custom-name-redis",
                "read",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-redis\n  Addon Type : redis",
            ),
        ],
    )
    def test_conduit_terraform_new_task(self, mode, addon_type, addon_name, access, info_message):
        self.setup()
        self.secrets_provider.get_addon_type.return_value = addon_type
        self.strategy_factory.detect_mode.return_value = mode
        strategy = MagicMock()
        strategy.get_data.return_value = {
            "cluster_arn": "cluster-arn",
            "task_def_family": "task-def-fam",
            "vpc_name": "vpc-name",
            "addon_type": addon_type,
            "access": access,
        }
        self.strategy_factory.create_strategy.return_value = strategy
        self.ecs_provider.get_ecs_task_arns.return_value = []
        self.ecs_provider.wait_for_task_to_register.return_value = ["task-arn"]

        # Test
        self.conduit.start("development", addon_name, access)

        # Checks
        self.session.client.assert_has_calls([call("ecs"), call("iam"), call("ssm")])
        self.secrets_provider.get_addon_type.assert_called_with(addon_name)
        self.strategy_factory.detect_mode.assert_called_with(
            self.ecs_client,
            "test-application",
            "development",
            addon_name,
            addon_type,
            access,
            self.io,
        )
        self.strategy_factory.create_strategy.assert_called_with(
            mode=mode,
            clients={"ecs": self.ecs_client, "iam": self.iam_client, "ssm": self.ssm_client},
            ecs_provider=self.ecs_provider,
            secrets_provider=self.secrets_provider,
            cloudformation_provider=self.cloudformation_provider,
            application=self.application,
            addon_name=addon_name,
            addon_type=addon_type,
            access=access,
            env="development",
            io=self.io,
        )
        strategy.get_data.assert_called_once()
        self.ecs_provider.get_ecs_task_arns.assert_called_with("cluster-arn", "task-def-fam")
        self.io.info.assert_has_calls(
            [
                call(info_message),
                call("Creating conduit ECS task..."),
                call("Waiting for ECS Exec agent to become available on the conduit task..."),
                call("Connecting to conduit task..."),
            ]
        )
        strategy.start_task.assert_called_with(
            {
                "cluster_arn": "cluster-arn",
                "task_def_family": "task-def-fam",
                "vpc_name": "vpc-name",
                "addon_type": addon_type,
                "access": access,
                "task_arns": [ANY],
            }
        )
        self.ecs_provider.wait_for_task_to_register.assert_called_with(
            "cluster-arn", "task-def-fam"
        )
        self.ecs_provider.ecs_exec_is_available.assert_called_with("cluster-arn", ["task-arn"])

        strategy.exec_task.assert_called_with(
            {
                "cluster_arn": "cluster-arn",
                "task_def_family": "task-def-fam",
                "vpc_name": "vpc-name",
                "addon_type": addon_type,
                "access": access,
                "task_arns": ["task-arn"],
            }
        )

    @pytest.mark.parametrize(
        "mode, addon_type, addon_name, access, info_message",
        [
            (
                "copilot",
                "postgres",
                "custom-name-postgres",
                "read",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-postgres\n  Addon Type : postgres\n  Access Level : read",
            ),
            (
                "copilot",
                "postgres",
                "custom-name-postgres",
                "write",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-postgres\n  Addon Type : postgres\n  Access Level : write",
            ),
            (
                "copilot",
                "postgres",
                "custom-name-postgres",
                "admin",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-postgres\n  Addon Type : postgres\n  Access Level : admin",
            ),
            (
                "copilot",
                "opensearch",
                "custom-name-opensearch",
                "read",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-opensearch\n  Addon Type : opensearch",
            ),
            (
                "copilot",
                "redis",
                "custom-name-redis",
                "read",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-redis\n  Addon Type : redis",
            ),
        ],
    )
    def test_conduit_terraform_existing_task(
        self, mode, addon_type, addon_name, access, info_message
    ):
        self.setup()
        self.secrets_provider.get_addon_type.return_value = addon_type
        self.strategy_factory.detect_mode.return_value = mode
        strategy = MagicMock()
        strategy.get_data.return_value = {
            "cluster_arn": "cluster-arn",
            "task_def_family": "task-def-fam",
            "vpc_name": "vpc-name",
            "addon_type": addon_type,
            "access": access,
        }
        self.strategy_factory.create_strategy.return_value = strategy
        self.ecs_provider.get_ecs_task_arns.return_value = ["task-arn"]

        # Test
        self.conduit.start("development", addon_name, access)

        # Checks
        self.session.client.assert_has_calls([call("ecs"), call("iam"), call("ssm")])
        self.secrets_provider.get_addon_type.assert_called_with(addon_name)
        self.strategy_factory.detect_mode.assert_called_with(
            self.ecs_client,
            "test-application",
            "development",
            addon_name,
            addon_type,
            access,
            self.io,
        )
        self.strategy_factory.create_strategy.assert_called_with(
            mode=mode,
            clients={"ecs": self.ecs_client, "iam": self.iam_client, "ssm": self.ssm_client},
            ecs_provider=self.ecs_provider,
            secrets_provider=self.secrets_provider,
            cloudformation_provider=self.cloudformation_provider,
            application=self.application,
            addon_name=addon_name,
            addon_type=addon_type,
            access=access,
            env="development",
            io=self.io,
        )
        strategy.get_data.assert_called_once()
        self.ecs_provider.get_ecs_task_arns.assert_called_with("cluster-arn", "task-def-fam")
        self.io.info.assert_has_calls(
            [
                call(info_message),
                call("Found a task already running: task-arn"),
                call("Waiting for ECS Exec agent to become available on the conduit task..."),
                call("Connecting to conduit task..."),
            ]
        )
        self.ecs_provider.ecs_exec_is_available.assert_called_with("cluster-arn", ["task-arn"])

        strategy.exec_task.assert_called_with(
            {
                "cluster_arn": "cluster-arn",
                "task_def_family": "task-def-fam",
                "vpc_name": "vpc-name",
                "addon_type": addon_type,
                "access": access,
                "task_arns": ["task-arn"],
            }
        )


class TestConduitCopilot:
    def setup(self):
        self.secrets_provider = MagicMock()
        self.cloudformation_provider = MagicMock()
        self.ecs_provider = MagicMock()
        self.io = MagicMock()
        self.strategy_factory = MagicMock()
        self.vpc_provider = MagicMock()

        self.ecs_client = MagicMock()
        self.iam_client = MagicMock()
        self.ssm_client = MagicMock()

        self.session = MagicMock()
        self.session.client.side_effect = lambda service: {
            "ecs": self.ecs_client,
            "iam": self.iam_client,
            "ssm": self.ssm_client,
        }.get(service)

        self.application = Application("test-application")
        self.application.environments = {
            "development": Environment("development", "000000000", {"000000000": self.session})
        }

        self.conduit = Conduit(
            self.application,
            self.secrets_provider,
            self.cloudformation_provider,
            self.ecs_provider,
            self.io,
            self.vpc_provider,
            self.strategy_factory,
        )

        self.strategy = MagicMock()

        self.strategy_factory.create_strategy.return_value = self.strategy

    @pytest.mark.parametrize(
        "mode, addon_type, addon_name, access, info_message",
        [
            (
                "copilot",
                "postgres",
                "custom-name-postgres",
                "read",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-postgres\n  Addon Type : postgres\n  Access Level : read",
            ),
            (
                "copilot",
                "postgres",
                "custom-name-postgres",
                "write",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-postgres\n  Addon Type : postgres\n  Access Level : write",
            ),
            (
                "copilot",
                "postgres",
                "custom-name-postgres",
                "admin",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-postgres\n  Addon Type : postgres\n  Access Level : admin",
            ),
            (
                "copilot",
                "opensearch",
                "custom-name-opensearch",
                "read",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-opensearch\n  Addon Type : opensearch",
            ),
            (
                "copilot",
                "redis",
                "custom-name-redis",
                "read",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-redis\n  Addon Type : redis",
            ),
        ],
    )
    def test_copilot_creates_new_task(self, mode, addon_type, addon_name, access, info_message):
        self.setup()
        self.secrets_provider.get_addon_type.return_value = addon_type
        self.strategy_factory.detect_mode.return_value = mode

        self.strategy.get_data.return_value = {
            "cluster_arn": "cluster-arn",
            "addon_type": addon_type,
            "task_def_family": "task-def-fam",
            "parameter_name": "param-name",
            "task_name": "task-name",
        }

        self.strategy_factory.create_strategy.return_value = self.strategy

        self.ecs_provider.get_ecs_task_arns.return_value = []
        self.ecs_provider.wait_for_task_to_register.return_value = ["task-arn"]

        self.conduit.start("development", addon_name, access)

        self.session.client.assert_has_calls([call("ecs"), call("iam"), call("ssm")])
        self.secrets_provider.get_addon_type.assert_called_with(addon_name)
        self.strategy_factory.detect_mode.assert_called_with(
            self.ecs_client,
            "test-application",
            "development",
            addon_name,
            addon_type,
            access,
            self.io,
        )
        self.strategy_factory.create_strategy.assert_called_with(
            mode=mode,
            clients={"ecs": self.ecs_client, "iam": self.iam_client, "ssm": self.ssm_client},
            ecs_provider=self.ecs_provider,
            secrets_provider=self.secrets_provider,
            cloudformation_provider=self.cloudformation_provider,
            application=self.application,
            addon_name=addon_name,
            addon_type=addon_type,
            access=access,
            env="development",
            io=self.io,
        )
        self.strategy.get_data.assert_called_once()
        self.ecs_provider.get_ecs_task_arns.assert_called_with("cluster-arn", "task-def-fam")
        self.io.info.assert_has_calls(
            [
                call(info_message),
                call("Creating conduit ECS task..."),
                call("Waiting for ECS Exec agent to become available on the conduit task..."),
                call("Connecting to conduit task..."),
            ]
        )
        self.strategy.start_task.assert_called_with(
            {
                "cluster_arn": "cluster-arn",
                "addon_type": addon_type,
                "task_def_family": "task-def-fam",
                "parameter_name": "param-name",
                "task_name": "task-name",
                "task_arns": ["task-arn"],
            }
        )
        self.ecs_provider.wait_for_task_to_register.assert_called_with(
            "cluster-arn", "task-def-fam"
        )
        self.ecs_provider.ecs_exec_is_available.assert_called_with("cluster-arn", ["task-arn"])

        self.strategy.exec_task.assert_called_with(
            {
                "cluster_arn": "cluster-arn",
                "addon_type": addon_type,
                "task_def_family": "task-def-fam",
                "parameter_name": "param-name",
                "task_name": "task-name",
                "task_arns": ["task-arn"],
            }
        )

    @pytest.mark.parametrize(
        "mode, addon_type, addon_name, access, info_message",
        [
            (
                "copilot",
                "postgres",
                "custom-name-postgres",
                "read",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-postgres\n  Addon Type : postgres\n  Access Level : read",
            ),
            (
                "copilot",
                "postgres",
                "custom-name-postgres",
                "write",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-postgres\n  Addon Type : postgres\n  Access Level : write",
            ),
            (
                "copilot",
                "postgres",
                "custom-name-postgres",
                "admin",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-postgres\n  Addon Type : postgres\n  Access Level : admin",
            ),
            (
                "copilot",
                "opensearch",
                "custom-name-opensearch",
                "read",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-opensearch\n  Addon Type : opensearch",
            ),
            (
                "copilot",
                "redis",
                "custom-name-redis",
                "read",
                "Checking if a conduit ECS task is already running for:\n  Addon Name : custom-name-redis\n  Addon Type : redis",
            ),
        ],
    )
    def test_copilot_uses_existing_task(self, mode, addon_type, addon_name, access, info_message):
        self.setup()
        self.secrets_provider.get_addon_type.return_value = addon_type
        self.strategy_factory.detect_mode.return_value = mode

        self.strategy.get_data.return_value = {
            "cluster_arn": "cluster-arn",
            "addon_type": addon_type,
            "task_def_family": "task-def-fam",
            "parameter_name": "param-name",
            "task_name": "task-name",
        }

        self.strategy_factory.create_strategy.return_value = self.strategy

        self.ecs_provider.get_ecs_task_arns.return_value = ["task-arn"]

        self.conduit.start("development", addon_name, access)

        self.session.client.assert_has_calls([call("ecs"), call("iam"), call("ssm")])
        self.secrets_provider.get_addon_type.assert_called_with(addon_name)
        self.strategy_factory.detect_mode.assert_called_with(
            self.ecs_client,
            "test-application",
            "development",
            addon_name,
            addon_type,
            access,
            self.io,
        )
        self.strategy_factory.create_strategy.assert_called_with(
            mode=mode,
            clients={"ecs": self.ecs_client, "iam": self.iam_client, "ssm": self.ssm_client},
            ecs_provider=self.ecs_provider,
            secrets_provider=self.secrets_provider,
            cloudformation_provider=self.cloudformation_provider,
            application=self.application,
            addon_name=addon_name,
            addon_type=addon_type,
            access=access,
            env="development",
            io=self.io,
        )
        self.strategy.get_data.assert_called_once()
        self.ecs_provider.get_ecs_task_arns.assert_called_with("cluster-arn", "task-def-fam")
        self.io.info.assert_has_calls(
            [
                call(info_message),
                call("Found a task already running: task-arn"),
                call("Waiting for ECS Exec agent to become available on the conduit task..."),
                call("Connecting to conduit task..."),
            ]
        )
        self.ecs_provider.ecs_exec_is_available.assert_called_with("cluster-arn", ["task-arn"])

        self.strategy.exec_task.assert_called_with(
            {
                "cluster_arn": "cluster-arn",
                "addon_type": addon_type,
                "task_def_family": "task-def-fam",
                "parameter_name": "param-name",
                "task_name": "task-name",
                "task_arns": ["task-arn"],
            }
        )


class ConduitMocks:
    def __init__(self, app_name="test-application", *args, **kwargs):

        session = Mock()
        sessions = {"000000000": session}
        dummy_application = Application(app_name)
        dummy_application.environments = {env: Environment(env, "000000000", sessions)}
        self.application = dummy_application
        self.secrets_provider = kwargs.get("secrets_provider", Mock())
        self.cloudformation_provider = kwargs.get("cloudformation_provider", Mock())
        self.ecs_provider = kwargs.get("ecs_provider", Mock())
        self.connect_to_addon_client_task = kwargs.get("connect_to_addon_client_task", Mock())
        self.create_addon_client_task = kwargs.get("create_addon_client_task", Mock())
        self.io = kwargs.get("io", Mock())
        self.subprocess = kwargs.get("subprocess", Mock(return_value="task_name"))
        self.vpc_provider = kwargs.get("vpc_provider", Mock())
        self.detect_mode = kwargs.get("detect_mode", Mock(return_value="copilot"))

    def params(self):
        return {
            "application": self.application,
            "secrets_provider": self.secrets_provider,
            "cloudformation_provider": self.cloudformation_provider,
            "ecs_provider": self.ecs_provider,
            # "connect_to_addon_client_task": self.connect_to_addon_client_task,
            # "create_addon_client_task": self.create_addon_client_task,
            "io": self.io,
            "vpc_provider": self.vpc_provider,
            "detect_mode": self.detect_mode,
        }


@pytest.mark.parametrize(
    "app_name, addon_type, addon_name, access",
    [
        ("app_1", "postgres", "custom-name-postgres", "read"),
        # ("app_2", "postgres", "custom-name-rds-postgres", "read"),
        # ("app_1", "redis", "custom-name-redis", "read"),
        # ("app_1", "opensearch", "custom-name-opensearch", "read"),
    ],
)
def test_conduit(app_name, addon_type, addon_name, access):
    conduit_mocks = ConduitMocks(app_name, addon_type)
    conduit_mocks.cloudformation_provider.update_conduit_stack_resources.return_value = (
        f"task-{task_name}"
    )
    conduit_mocks.ecs_provider.get_cluster_arn.return_value = cluster_arn
    conduit_mocks.ecs_provider.get_or_create_task_name.return_value = task_name
    conduit_mocks.ecs_provider.get_ecs_task_arns.return_value = []
    conduit_mocks.secrets_provider.get_parameter_name.return_value = "parameter_name"
    conduit_mocks.secrets_provider.get_addon_type.return_value = addon_type
    conduit = Conduit(**conduit_mocks.params())

    # TODO: DBTP-1971: Should be able to lose these during future refactorings
    conduit.application.environments[env].session.client("ecs")
    conduit.application.environments[env].session.client("ssm")
    conduit.application.environments[env].session.client("iam")

    conduit.start(env, addon_name, access)

    conduit.ecs_provider.get_ecs_task_arns.assert_has_calls(
        [call(cluster_arn, task_name), call(cluster_arn, task_name)]
    )
    # conduit.connect_to_addon_client_task.assert_called_once_with(
    #     ecs_client, conduit.subprocess, app_name, env, cluster_arn, task_name
    # )
    conduit.secrets_provider.get_addon_type.assert_called_once_with(addon_name)
    conduit.ecs_provider.get_cluster_arn.assert_called_once()
    conduit.ecs_provider.get_or_create_task_name.assert_called_once_with(
        addon_name, "parameter_name"
    )
    conduit.cloudformation_provider.add_stack_delete_policy_to_task_role.assert_called_once_with(
        task_name
    )
    conduit.cloudformation_provider.update_conduit_stack_resources.assert_called_once_with(
        app_name,
        env,
        addon_type,
        addon_name,
        task_name,
        "parameter_name",
        access,
    )
    conduit.cloudformation_provider.wait_for_cloudformation_to_reach_status.assert_called_once_with(
        "stack_update_complete", f"task-{task_name}"
    )
    # conduit.create_addon_client_task.assert_called_once_with(
    #     iam_client,
    #     ssm_client,
    #     conduit.subprocess,
    #     conduit.application,
    #     env,
    #     addon_type,
    #     addon_name,
    #     task_name,
    #     access,
    # )
    conduit_mocks.io.info.assert_has_calls(
        [
            call("Creating conduit task"),
            call("Updating conduit task"),
            call("Waiting for conduit task update to complete..."),
            call("Checking if exec is available for conduit task..."),
            call("Connecting to conduit task"),
        ]
    )


def test_conduit_with_task_already_running():
    conduit_mocks = ConduitMocks(app_name, addon_type)
    conduit_mocks.ecs_provider.get_cluster_arn.return_value = cluster_arn
    conduit_mocks.ecs_provider.get_or_create_task_name.return_value = task_name
    conduit_mocks.ecs_provider.get_ecs_task_arns.return_value = [
        "arn:aws:ecs:eu-west-2:12345678:task/does-not-matter/1234qwer"
    ]
    conduit_mocks.secrets_provider.get_parameter_name.return_value = "parameter_name"
    conduit_mocks.secrets_provider.get_addon_type.return_value = "postgres"
    conduit = Conduit(**conduit_mocks.params())
    # TODO: DBTP-1971: This client can go during further refactoring
    ecs_client = conduit.application.environments[env].session.client("ecs")

    conduit.start(env, addon_name, "read")

    conduit.ecs_provider.get_ecs_task_arns.assert_called_once_with(cluster_arn, task_name)
    conduit.connect_to_addon_client_task.assert_called_once_with(
        ecs_client, conduit.subprocess, app_name, env, cluster_arn, task_name
    )
    conduit.secrets_provider.get_addon_type.assert_called_once_with(addon_name)
    conduit.ecs_provider.get_cluster_arn.assert_called_once()
    conduit.ecs_provider.get_or_create_task_name.assert_called_once_with(
        addon_name, "parameter_name"
    )
    conduit.cloudformation_provider.add_stack_delete_policy_to_task_role.assert_not_called()
    conduit.cloudformation_provider.update_conduit_stack_resources.assert_not_called()
    conduit.create_addon_client_task.assert_not_called()

    conduit_mocks.io.info.assert_has_calls(
        [
            call("Checking if a conduit task is already running for postgres"),
            call("Conduit task already running"),
            call("Checking if exec is available for conduit task..."),
            call("Connecting to conduit task"),
        ]
    )


def test_conduit_domain_when_no_cluster_exists():
    conduit_mocks = ConduitMocks(app_name, addon_type)
    conduit_mocks.ecs_provider.get_cluster_arn.side_effect = NoClusterException(
        application_name=app_name,
        environment=env,
    )
    conduit = Conduit(**conduit_mocks.params())

    with pytest.raises(NoClusterException):
        conduit.start(env, addon_name)
        conduit.secrets_provider.get_addon_type.assert_called_once_with(addon_name)
        conduit.ecs_provider.get_cluster_arn.assert_called_once()


def test_conduit_domain_when_no_connection_secret_exists():
    conduit_mocks = ConduitMocks(
        app_name,
        addon_type,
    )
    conduit_mocks.ecs_provider.get_ecs_task_arns.return_value = []
    conduit_mocks.secrets_provider.get_parameter_name.return_value = "parameter_name"
    conduit_mocks.create_addon_client_task.side_effect = SecretNotFoundException(
        f"/copilot/{app_name}/{env}/secrets/{addon_name}"
    )
    conduit = Conduit(**conduit_mocks.params())

    with pytest.raises(SecretNotFoundException):
        conduit.start(env, addon_name)

        conduit.secrets_provider.get_addon_type.assert_called_once_with(addon_name)
        conduit.ecs_provider.get_cluster_arn.assert_called_once()
        conduit.ecs_provider.get_or_create_task_name.assert_called_once_with(
            addon_name, "parameter_name"
        )


def test_conduit_domain_when_client_task_fails_to_start():
    conduit_mocks = ConduitMocks(
        app_name,
        addon_type,
    )
    conduit_mocks.connect_to_addon_client_task.side_effect = (
        CreateTaskTimeoutException(
            addon_name=addon_name,
            application_name=app_name,
            environment=env,
        ),
    )

    conduit = Conduit(**conduit_mocks.params())

    with pytest.raises(CreateTaskTimeoutException):
        conduit.start(env, addon_name)
        conduit.ecs_provider.get_ecs_task_arns.assert_called_once_with(cluster_arn, task_name)
        conduit.connect_to_addon_client_task.assert_called_once_with(
            conduit.subprocess, app_name, env, cluster_arn, task_name
        )
        conduit.secrets_provider.get_addon_type.assert_called_once_with(app_name, env, addon_name)
        conduit.ecs_provider.get_cluster_arn.assert_called_once()
        conduit.ecs_provider.get_or_create_task_name.assert_called_once_with(
            addon_name, "parameter_name"
        )
        conduit.create_addon_client_task.assert_not_called()
        conduit.cloudformation_provider.add_stack_delete_policy_to_task_role.assert_not_called()
        conduit.cloudformation_provider.update_conduit_stack_resources.assert_not_called()


def test_conduit_domain_when_addon_type_is_invalid():
    addon_name = "invalid_addon"
    addon_type = "invalid_addon_type"

    conduit_mocks = ConduitMocks(app_name, addon_type)

    conduit_mocks.secrets_provider.get_addon_type.side_effect = InvalidAddonTypeException(
        addon_type
    )
    conduit = Conduit(**conduit_mocks.params())
    conduit.application.environments[env].session.client("ecs")

    with pytest.raises(InvalidAddonTypeException):
        conduit.start(env, addon_name)
        conduit.ecs_provider.get_ecs_task_arns.assert_called_once_with(cluster_arn, task_name)


def test_start_with_addon_does_not_exist_raises_error():
    addon_name = "addon_doesnt_exist"
    conduit_mocks = ConduitMocks(app_name, addon_type)
    conduit_mocks.secrets_provider.get_addon_type.side_effect = AddonNotFoundException(addon_name)

    conduit = Conduit(**conduit_mocks.params())

    with pytest.raises(AddonNotFoundException):
        conduit.start(env, addon_name)


def test_conduit_domain_when_no_addon_config_parameter_exists():
    addon_name = "parameter_doesnt_exist"
    conduit_mocks = ConduitMocks(app_name, addon_type)

    conduit_mocks.secrets_provider.get_addon_type.side_effect = ParameterNotFoundException(
        application_name=app_name,
        environment=env,
    )

    conduit = Conduit(**conduit_mocks.params())
    conduit.application.environments[env].session.client("ecs")

    with pytest.raises(ParameterNotFoundException):
        conduit.start(env, addon_name)
        conduit.ecs_provider.get_ecs_task_arns.assert_called_once_with(cluster_arn, task_name)


def test_conduit_domain_ecs_exec_agent_does_not_start():
    conduit_mocks = ConduitMocks(
        app_name,
        addon_type,
    )

    conduit_mocks.ecs_provider.get_ecs_task_arns.return_value = [
        "arn:aws:ecs:eu-west-2:123456789012:task/MyTaskARN"
    ]
    conduit_mocks.ecs_provider.ecs_exec_is_available.side_effect = ECSAgentNotRunningException()
    conduit_mocks.ecs_provider.get_cluster_arn.return_value = cluster_arn

    conduit = Conduit(**conduit_mocks.params())
    conduit.application.environments[env].session.client("ecs")

    with pytest.raises(ECSAgentNotRunningException):
        conduit.start(env, addon_name)

    conduit.ecs_provider.ecs_exec_is_available.assert_called_once_with(
        cluster_arn,
        ["arn:aws:ecs:eu-west-2:123456789012:task/MyTaskARN"],
    )
