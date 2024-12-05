from unittest.mock import Mock
from unittest.mock import call

import pytest

from dbt_platform_helper.domain.conduit import Conduit
from dbt_platform_helper.legacy_exceptions import AddonNotFoundError
from dbt_platform_helper.legacy_exceptions import CreateTaskTimeoutError
from dbt_platform_helper.providers.ecs import ECSAgentNotRunning
from dbt_platform_helper.providers.ecs import NoClusterError
from dbt_platform_helper.providers.secrets import InvalidAddonTypeError
from dbt_platform_helper.providers.secrets import ParameterNotFoundError
from dbt_platform_helper.providers.secrets import SecretNotFoundError
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import Environment

app_name = "failed_app"
addon_name = "important-db"
addon_type = "postgres"
env = "development"
cluster_arn = "arn:aws:ecs:eu-west-2:123456789012:cluster/MyECSCluster1"
task_name = "task_name"
addon_name = "custom-name-rds-postgres"


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
        self.echo = kwargs.get("echo", Mock())
        self.subprocess = kwargs.get("subprocess", Mock(return_value="task_name"))

    def params(self):
        return {
            "application": self.application,
            "secrets_provider": self.secrets_provider,
            "cloudformation_provider": self.cloudformation_provider,
            "ecs_provider": self.ecs_provider,
            "connect_to_addon_client_task": self.connect_to_addon_client_task,
            "create_addon_client_task": self.create_addon_client_task,
            "echo": self.echo,
            "subprocess": self.subprocess,
        }


@pytest.mark.parametrize(
    "app_name, addon_type, addon_name, access",
    [
        ("app_1", "postgres", "custom-name-postgres", "read"),
        ("app_2", "postgres", "custom-name-rds-postgres", "read"),
        ("app_1", "redis", "custom-name-redis", "read"),
        ("app_1", "opensearch", "custom-name-opensearch", "read"),
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

    # Todo: Should be able to lose these during future refactorings
    ecs_client = conduit.application.environments[env].session.client("ecs")
    ssm_client = conduit.application.environments[env].session.client("ssm")
    iam_client = conduit.application.environments[env].session.client("iam")

    conduit.start(env, addon_name, access)

    conduit.ecs_provider.get_ecs_task_arns.assert_has_calls(
        [call(cluster_arn, task_name), call(cluster_arn, task_name)]
    )
    conduit.connect_to_addon_client_task.assert_called_once_with(
        ecs_client, conduit.subprocess, app_name, env, cluster_arn, task_name
    )
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
    conduit.create_addon_client_task.assert_called_once_with(
        iam_client,
        ssm_client,
        conduit.subprocess,
        conduit.application,
        env,
        addon_type,
        addon_name,
        task_name,
        access,
    )
    conduit_mocks.echo.assert_has_calls(
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
    # Todo: This client can go during further refactoring
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

    conduit_mocks.echo.assert_has_calls(
        [
            call("Checking if a conduit task is already running for postgres"),
            call("Conduit task already running"),
            call("Checking if exec is available for conduit task..."),
            call("Connecting to conduit task"),
        ]
    )


def test_conduit_domain_when_no_cluster_exists():
    conduit_mocks = ConduitMocks(app_name, addon_type)
    conduit_mocks.ecs_provider.get_cluster_arn.side_effect = NoClusterError(
        application_name=app_name,
        environment=env,
    )
    conduit = Conduit(**conduit_mocks.params())

    with pytest.raises(NoClusterError):
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
    conduit_mocks.create_addon_client_task.side_effect = SecretNotFoundError(
        f"/copilot/{app_name}/{env}/secrets/{addon_name}"
    )
    conduit = Conduit(**conduit_mocks.params())

    with pytest.raises(SecretNotFoundError):
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
        CreateTaskTimeoutError(
            addon_name=addon_name,
            application_name=app_name,
            environment=env,
        ),
    )

    conduit = Conduit(**conduit_mocks.params())

    with pytest.raises(CreateTaskTimeoutError):
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

    conduit_mocks.secrets_provider.get_addon_type.side_effect = InvalidAddonTypeError(addon_type)
    conduit = Conduit(**conduit_mocks.params())
    conduit.application.environments[env].session.client("ecs")

    with pytest.raises(InvalidAddonTypeError):
        conduit.start(env, addon_name)
        conduit.ecs_provider.get_ecs_task_arns.assert_called_once_with(cluster_arn, task_name)


def test_start_with_addon_does_not_exist_raises_error():
    addon_name = "addon_doesnt_exist"
    conduit_mocks = ConduitMocks(app_name, addon_type)
    conduit_mocks.secrets_provider.get_addon_type.side_effect = AddonNotFoundError(addon_name)

    conduit = Conduit(**conduit_mocks.params())

    with pytest.raises(AddonNotFoundError):
        conduit.start(env, addon_name)


def test_conduit_domain_when_no_addon_config_parameter_exists():
    addon_name = "parameter_doesnt_exist"
    conduit_mocks = ConduitMocks(app_name, addon_type)

    conduit_mocks.secrets_provider.get_addon_type.side_effect = ParameterNotFoundError(
        application_name=app_name,
        environment=env,
    )

    conduit = Conduit(**conduit_mocks.params())
    conduit.application.environments[env].session.client("ecs")

    with pytest.raises(ParameterNotFoundError):
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
    conduit_mocks.ecs_provider.ecs_exec_is_available.side_effect = ECSAgentNotRunning()
    conduit_mocks.ecs_provider.get_cluster_arn.return_value = cluster_arn

    conduit = Conduit(**conduit_mocks.params())
    conduit.application.environments[env].session.client("ecs")

    with pytest.raises(ECSAgentNotRunning):
        conduit.start(env, addon_name)

    conduit.ecs_provider.ecs_exec_is_available.assert_called_once_with(
        cluster_arn,
        ["arn:aws:ecs:eu-west-2:123456789012:task/MyTaskARN"],
    )
