from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import call

import pytest

from dbt_platform_helper.domain.conduit import Conduit
from dbt_platform_helper.domain.conduit import CopilotConduitStrategy
from dbt_platform_helper.domain.conduit import TerraformConduitStrategy
from dbt_platform_helper.providers.vpc import Vpc
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


class TestTerraformConduitStrategy:
    def setup(self):

        self.ecs_provider = MagicMock()
        self.io = MagicMock()
        self.vpc_provider = MagicMock()
        self.get_postgres_admin_connection_string = MagicMock()

        self.ssm_client = MagicMock()

        self.ssm_client.get_parameter.return_value = {"Parameter": {"Value": "vpc-name"}}
        self.clients = {"ecs": MagicMock(), "iam": MagicMock(), "ssm": self.ssm_client}

        self.session = MagicMock()
        self.application = Application("test-application")
        self.application.environments = {
            "development": Environment("development", "000000000", {"000000000": self.session})
        }

        self.strategy = TerraformConduitStrategy(
            self.clients,
            self.ecs_provider,
            self.application,
            "custom-name-postgres",
            "postgres",
            "read",
            "development",
            self.io,
            self.vpc_provider,
            self.get_postgres_admin_connection_string,
        )

    def test_strategy_methods(self):
        self.setup()
        self.ecs_provider.get_cluster_arn_by_name.return_value = "cluster-arn"
        vpc_instance = MagicMock()
        vpc_instance.get_vpc.return_value = Vpc(
            "id", ["public-subnets"], ["private-subnets"], ["security-groups"]
        )
        self.vpc_provider.return_value = vpc_instance
        # self.get_postgres_admin_connection_string.return_value = "connection-string"

        result = self.strategy.get_data()

        assert result == {
            "cluster_arn": "cluster-arn",
            "task_def_family": "conduit-postgres-read-test-application-development-custom-name-postgres",
            "vpc_name": "vpc-name",
            "addon_type": "postgres",
            "access": "read",
        }

        self.io.info.assert_has_calls(
            [
                call("Starting conduit in Terraform mode."),
            ]
        )

        self.strategy.start_task(result)

        self.ecs_provider.start_ecs_task.assert_called_with(
            "test-application-development",
            "conduit-postgres-read-test-application-development-custom-name-postgres",
            "conduit-postgres-read-test-application-development-custom-name-postgres",
            Vpc("id", ["public-subnets"], ["private-subnets"], ["security-groups"]),
            None,
        )

        result["task_arns"] = ["task-arn"]
        self.strategy.exec_task(result)

        self.ecs_provider.exec_task.assert_called_with("cluster-arn", "task-arn")

    def test_strategy_postgres_admin(self):
        self.setup()
        self.ecs_provider.get_cluster_arn_by_name.return_value = "cluster-arn"

        vpc_instance = MagicMock()
        vpc_instance.get_vpc.return_value = Vpc(
            "id", ["public-subnets"], ["private-subnets"], ["security-groups"]
        )
        self.vpc_provider.return_value = vpc_instance

        # Postgres admin scenario
        self.strategy.access = "admin"
        self.strategy.addon_type = "postgres"

        data_context = {
            "cluster_arn": "cluster-arn",
            "task_def_family": "conduit-postgres-admin-test-application-development-custom-name-postgres",
            "vpc_name": "vpc-name",
            "addon_type": "postgres",
            "access": "admin",
        }

        # Execute
        self.strategy.start_task(data_context)

        # Validate
        self.get_postgres_admin_connection_string.assert_called_once_with(
            self.clients["ssm"],
            "/copilot/test-application/development/secrets/CUSTOM_NAME_POSTGRES",
            self.application,
            "development",
            "custom-name-postgres",
        )


class TestCopilotConduitStrategy:

    def setup(self):
        self.secrets_provider = MagicMock()
        self.cloudformation_provider = MagicMock()
        self.ecs_provider = MagicMock()
        self.io = MagicMock()

        self.clients = {"ecs": MagicMock(), "iam": MagicMock(), "ssm": MagicMock()}
        self.connect_to_addon_client_task = MagicMock()
        self.create_addon_client_task = MagicMock()

        self.session = MagicMock()
        self.application = Application("test-application")
        self.application.environments = {
            "development": Environment("development", "000000000", {"000000000": self.session})
        }

        self.strategy = CopilotConduitStrategy(
            self.clients,
            self.ecs_provider,
            self.secrets_provider,
            self.cloudformation_provider,
            self.application,
            "custom-name-postgres",
            "read",
            "development",
            self.io,
            self.connect_to_addon_client_task,
            self.create_addon_client_task,
        )

    def test_strategy_methods(self):
        self.setup()
        self.secrets_provider.get_addon_type.return_value = "postgres"
        self.secrets_provider.get_parameter_name.return_value = "parameter-name"
        self.ecs_provider.get_or_create_task_name.return_value = "task-name"
        self.ecs_provider.get_cluster_arn_by_copilot_tag.return_value = "cluster-arn"

        self.cloudformation_provider.update_conduit_stack_resources.return_value = "stack-name"

        result = self.strategy.get_data()

        assert result == {
            "cluster_arn": "cluster-arn",
            "addon_type": "postgres",
            "task_def_family": "copilot-task-name",
            "parameter_name": "parameter-name",
            "task_name": "task-name",
        }

        self.strategy.start_task(result)

        self.create_addon_client_task.assert_called_with(
            self.clients["iam"],
            self.clients["ssm"],
            self.application,
            "development",
            "postgres",
            "custom-name-postgres",
            "task-name",
            "read",
        )
        self.io.info.assert_has_calls(
            [
                call("Updating conduit task"),
                call("Waiting for conduit task update to complete..."),
            ]
        )
        self.cloudformation_provider.add_stack_delete_policy_to_task_role.assert_called_with(
            "task-name"
        )
        self.cloudformation_provider.update_conduit_stack_resources.assert_called_with(
            "test-application",
            "development",
            "postgres",
            "custom-name-postgres",
            "task-name",
            "parameter-name",
            "read",
        )
        self.cloudformation_provider.wait_for_cloudformation_to_reach_status.assert_called_with(
            "stack_update_complete", "stack-name"
        )

        self.strategy.exec_task(result)

        self.connect_to_addon_client_task.assert_called_with(
            self.clients["ecs"], "test-application", "development", "cluster-arn", "task-name"
        )
