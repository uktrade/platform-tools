from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import call

import pytest

from dbt_platform_helper.domain.conduit import Conduit
from dbt_platform_helper.exceptions import AddonNotFoundError
from dbt_platform_helper.exceptions import CreateTaskTimeoutError
from dbt_platform_helper.exceptions import ECSAgentNotRunning
from dbt_platform_helper.exceptions import InvalidAddonTypeError
from dbt_platform_helper.exceptions import NoClusterError
from dbt_platform_helper.exceptions import ParameterNotFoundError
from dbt_platform_helper.exceptions import SecretNotFoundError
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import Environment

app_name = "failed_app"
addon_name = "important-db"
addon_type = "postgres"
env = "development"
cluster_name = "arn:aws:ecs:eu-west-2:123456789012:cluster/MyECSCluster1"
task_name = "task_name"
addon_name = "custom-name-rds-postgres"


class ConduitMocks:
    def __init__(self, app_name="test-application", addon_type="postgres", *args, **kwargs):

        session = Mock()
        sessions = {"000000000": session}
        dummy_application = Application(app_name)
        dummy_application.environments = {env: Environment(env, "000000000", sessions)}
        self.add_stack_delete_policy_to_task_role_fn = kwargs.get(
            "add_stack_delete_policy_to_task_role_fn", Mock()
        )
        self.get_ecs_task_arns_fn = kwargs.get("get_ecs_task_arns_fn", Mock(return_value=[]))
        self.application = dummy_application
        self.secrets_provider = kwargs.get("secrets_provider", Mock())
        self.ecs_exec_is_available_fn = kwargs.get("ecs_exec_is_available_fn", Mock())
        self.connect_to_addon_client_task_fn = kwargs.get("connect_to_addon_client_task_fn", Mock())
        self.create_addon_client_task_fn = kwargs.get("create_addon_client_task_fn", Mock())
        self.create_postgres_admin_task_fn = kwargs.get("create_postgres_admin_task_fn", Mock())
        self.echo_fn = kwargs.get("echo_fn", Mock())
        # self.get_addon_type_fn = kwargs.get("get_addon_type_fn", Mock(return_value=addon_type))
        self.get_cluster_arn_fn = kwargs.get(
            "get_cluster_arn_fn",
            Mock(return_value="arn:aws:ecs:eu-west-2:123456789012:cluster/MyECSCluster1"),
        )
        self.get_or_create_task_name_fn = kwargs.get(
            "get_or_create_task_name_fn", Mock(return_value="task_name")
        )
        # self.get_parameter_name_fn = kwargs.get(
        #     "get_parameter_name", Mock(return_value="parameter_name")
        # )
        self.subprocess = kwargs.get("subprocess", Mock(return_value="task_name"))
        self.update_conduit_stack_resources_fn = kwargs.get(
            "update_conduit_stack_resources_fn", Mock(return_value=f"task-{task_name}")
        )
        self.wait_for_cloudformation_to_reach_status_fn = kwargs.get(
            "wait_for_cloudformation_to_reach_status_fn", Mock()
        )

    def params(self):
        return {
            "add_stack_delete_policy_to_task_role_fn": self.add_stack_delete_policy_to_task_role_fn,
            "get_ecs_task_arns_fn": self.get_ecs_task_arns_fn,
            "application": self.application,
            "secrets_provider": self.secrets_provider,
            "ecs_exec_is_available_fn": self.ecs_exec_is_available_fn,
            "connect_to_addon_client_task_fn": self.connect_to_addon_client_task_fn,
            "create_addon_client_task_fn": self.create_addon_client_task_fn,
            "create_postgres_admin_task_fn": self.create_postgres_admin_task_fn,
            "echo_fn": self.echo_fn,
            # "get_addon_type_fn": self.get_addon_type_fn,
            "get_cluster_arn_fn": self.get_cluster_arn_fn,
            "get_or_create_task_name_fn": self.get_or_create_task_name_fn,
            # "get_parameter_name_fn": self.get_parameter_name_fn,
            "subprocess_fn": self.subprocess,
            "update_conduit_stack_resources_fn": self.update_conduit_stack_resources_fn,
            "wait_for_cloudformation_to_reach_status_fn": self.wait_for_cloudformation_to_reach_status_fn,
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
    secrets_provider_mock = Mock()
    secrets_provider_mock.get_parameter_name.return_value = "parameter_name"
    secrets_provider_mock.get_addon_type.return_value = addon_type
    conduit_mocks = ConduitMocks(app_name, addon_type, secrets_provider=secrets_provider_mock)

    # TODO - update mocks as below for secrets provider
    # conduit_mocks.secrets_provider.get_parameter_name.return_value = "parameter_name"
    # conduit_mocks.secrets_provider.get_addon_type.return_value = "postgres"

    conduit = Conduit(**conduit_mocks.params())
    ecs_client = conduit.application.environments[env].session.client("ecs")
    ssm_client = conduit.application.environments[env].session.client("ssm")
    cloudformation_client = conduit.application.environments[env].session.client("cloudformation")
    iam_client = conduit.application.environments[env].session.client("iam")
    secretsmanager_client = conduit.application.environments[env].session.client("secretsmanager")

    conduit.start(env, addon_name, access)

    conduit.get_ecs_task_arns_fn.assert_has_calls(
        [call(ecs_client, cluster_name, task_name), call(ecs_client, cluster_name, task_name)]
    )
    conduit.connect_to_addon_client_task_fn.assert_called_once_with(
        ecs_client, conduit.subprocess_fn, app_name, env, cluster_name, task_name
    )
    conduit.secrets_provider.get_addon_type.assert_called_once_with(addon_name)
    conduit.get_cluster_arn_fn.assert_called_once_with(ecs_client, app_name, env)

    # TODO - will need fixing when the ECS object is instantiated, only expects two params now. addon_name, "parameter_name"
    conduit.get_or_create_task_name_fn.assert_called_once_with(
        ssm_client, app_name, env, addon_name, "parameter_name"
    )

    conduit.add_stack_delete_policy_to_task_role_fn.assert_called_once_with(
        cloudformation_client, iam_client, task_name
    )
    conduit.update_conduit_stack_resources_fn.assert_called_once_with(
        cloudformation_client,
        iam_client,
        ssm_client,
        app_name,
        env,
        addon_type,
        addon_name,
        task_name,
        "parameter_name",
        access,
    )
    conduit.wait_for_cloudformation_to_reach_status_fn.assert_called_once_with(
        cloudformation_client, "stack_update_complete", f"task-{task_name}"
    )
    conduit.create_addon_client_task_fn.assert_called_once_with(
        iam_client,
        ssm_client,
        secretsmanager_client,
        conduit.subprocess_fn,
        conduit.application,
        env,
        addon_type,
        addon_name,
        task_name,
        access,
    )

    conduit_mocks.echo_fn.assert_has_calls(
        [
            call("Creating conduit task"),
            call("Updating conduit task"),
            call("Waiting for conduit task update to complete..."),
            call("Checking if exec is available for conduit task..."),
            call("Connecting to conduit task"),
        ]
    )


def test_conduit_with_task_already_running():
    conduit_mocks = ConduitMocks(
        app_name,
        addon_type,
        get_ecs_task_arns_fn=MagicMock(
            return_value=["arn:aws:ecs:eu-west-2:12345678:task/does-not-matter/1234qwer"]
        ),
    )

    conduit_mocks.secrets_provider.get_parameter_name.return_value = "parameter_name"
    conduit_mocks.secrets_provider.get_addon_type.return_value = "postgres"

    conduit = Conduit(**conduit_mocks.params())
    ecs_client = conduit.application.environments[env].session.client("ecs")
    ssm_client = conduit.application.environments[env].session.client("ssm")

    conduit.start(env, addon_name, "read")

    conduit.get_ecs_task_arns_fn.assert_called_once_with(ecs_client, cluster_name, task_name)
    conduit.connect_to_addon_client_task_fn.assert_called_once_with(
        ecs_client, conduit.subprocess_fn, app_name, env, cluster_name, task_name
    )
    conduit.secrets_provider.get_addon_type.assert_called_once_with(addon_name)
    conduit.get_cluster_arn_fn.assert_called_once_with(ecs_client, app_name, env)
    # Todo: Looks like we need to mock get_parameter_name()
    conduit.get_or_create_task_name_fn.assert_called_once_with(
        ssm_client, app_name, env, addon_name, "parameter_name"
    )
    conduit.add_stack_delete_policy_to_task_role_fn.assert_not_called()
    conduit.update_conduit_stack_resources_fn.assert_not_called()
    conduit.create_addon_client_task_fn.assert_not_called()

    conduit_mocks.echo_fn.assert_has_calls(
        [
            call("Checking if a conduit task is already running for postgres"),
            call("Conduit task already running"),
            call("Checking if exec is available for conduit task..."),
            call("Connecting to conduit task"),
        ]
    )


def test_conduit_domain_when_no_cluster_exists():
    conduit_mocks = ConduitMocks(
        app_name,
        addon_type,
        get_cluster_arn_fn=Mock(
            side_effect=NoClusterError(application_name=app_name, environment=env)
        ),
    )
    conduit = Conduit(**conduit_mocks.params())
    ecs_client = conduit.application.environments[env].session.client("ecs")
    ssm_client = conduit.application.environments[env].session.client("ssm")

    with pytest.raises(NoClusterError):
        conduit.start(env, addon_name)
        conduit.secrets_provider.assert_called_once_with(ssm_client, app_name, env, addon_name)
        conduit.get_cluster_arn_fn.assert_called_once_with(ecs_client, app_name, env)


def test_conduit_domain_when_no_connection_secret_exists():
    conduit_mocks = ConduitMocks(
        app_name,
        addon_type,
        get_ecs_task_arns_fn=Mock(return_value=False),
        create_addon_client_task_fn=Mock(
            side_effect=SecretNotFoundError(f"/copilot/{app_name}/{env}/secrets/{addon_name}")
        ),
    )

    conduit = Conduit(**conduit_mocks.params())
    ecs_client = conduit.application.environments[env].session.client("ecs")
    ssm_client = conduit.application.environments[env].session.client("ssm")

    with pytest.raises(SecretNotFoundError):
        conduit.start(env, addon_name)
        conduit.secrets_provider.assert_called_once_with(ssm_client, app_name, env, addon_name)
        conduit.get_cluster_arn_fn.assert_called_once_with(ecs_client, app_name, env)
        conduit.get_cluster_arn_fn.assert_called_once_with(ecs_client, app_name, env)
        conduit.get_or_create_task_name_fn.assert_called_once_with(
            ssm_client, app_name, env, addon_name, "parameter_name"
        )


def test_conduit_domain_when_client_task_fails_to_start():
    conduit_mocks = ConduitMocks(
        app_name,
        addon_type,
        connect_to_addon_client_task_fn=Mock(
            side_effect=CreateTaskTimeoutError(
                addon_name=addon_name,
                application_name=app_name,
                environment=env,
            )
        ),
    )
    conduit = Conduit(**conduit_mocks.params())
    ecs_client = conduit.application.environments[env].session.client("ecs")
    ssm_client = conduit.application.environments[env].session.client("ssm")

    with pytest.raises(CreateTaskTimeoutError):
        conduit.start(env, addon_name)
        conduit.get_ecs_task_arns_fn.assert_called_once_with(ecs_client, cluster_name, task_name)
        conduit.connect_to_addon_client_task_fn.assert_called_once_with(
            ecs_client, conduit.subprocess_fn, app_name, env, cluster_name, task_name
        )
        conduit.secrets_provider.assert_called_once_with(ssm_client, app_name, env, addon_name)
        conduit.get_cluster_arn_fn.assert_called_once_with(ecs_client, app_name, env)
        conduit.get_or_create_task_name_fn.assert_called_once_with(
            ssm_client, app_name, env, addon_name, "parameter_name"
        )
        conduit.create_addon_client_task_fn.assert_not_called()
        conduit.add_stack_delete_policy_to_task_role_fn.assert_not_called()
        conduit.update_conduit_stack_resources_fn.assert_not_called()


def test_conduit_domain_when_addon_type_is_invalid():
    addon_name = "invalid_addon"
    addon_type = "invalid_addon_type"

    # TODO - update mocks as below.
    secrets_provider_mock = Mock()
    secrets_provider_mock.get_addon_type.side_effect = InvalidAddonTypeError(addon_type)
    conduit_mocks = ConduitMocks(
        app_name,
        addon_type,
        secrets_provider=secrets_provider_mock,
    )

    conduit = Conduit(**conduit_mocks.params())
    ecs_client = conduit.application.environments[env].session.client("ecs")

    with pytest.raises(InvalidAddonTypeError):
        conduit.start(env, addon_name)
        conduit.get_ecs_task_arns_fn.assert_called_once_with(ecs_client, cluster_name, task_name)


# Todo: does this belong in the Secrets provider
def test_start_with_addon_does_not_exist_raises_error():
    addon_name = "addon_doesnt_exist"
    secrets_provider_mock = Mock()
    secrets_provider_mock.get_addon_type.side_effect = AddonNotFoundError(addon_name)
    conduit_mocks = ConduitMocks(app_name, addon_type, secrets_provider=secrets_provider_mock)

    conduit = Conduit(**conduit_mocks.params())

    with pytest.raises(AddonNotFoundError):
        conduit.start(env, addon_name)


def test_conduit_domain_when_no_addon_config_parameter_exists():
    addon_name = "parameter_doesnt_exist"
    secrets_provider_mock = Mock()
    secrets_provider_mock.get_addon_type.side_effect = ParameterNotFoundError(
        application_name=app_name,
        environment=env,
    )
    conduit_mocks = ConduitMocks(
        app_name,
        addon_type,
        secrets_provider=secrets_provider_mock,
    )

    conduit = Conduit(**conduit_mocks.params())
    ecs_client = conduit.application.environments[env].session.client("ecs")

    with pytest.raises(ParameterNotFoundError):
        conduit.start(env, addon_name)
        conduit.get_ecs_task_arns_fn.assert_called_once_with(ecs_client, cluster_name, task_name)


def test_conduit_domain_ecs_exec_agent_does_not_start():
    conduit_mocks = ConduitMocks(
        app_name,
        addon_type,
        get_ecs_task_arns_fn=Mock(
            return_value=["arn:aws:ecs:eu-west-2:123456789012:task/MyTaskARN"]
        ),
        ecs_exec_is_available_fn=Mock(side_effect=ECSAgentNotRunning()),
    )
    conduit = Conduit(**conduit_mocks.params())
    ecs_client = conduit.application.environments[env].session.client("ecs")

    with pytest.raises(ECSAgentNotRunning):
        conduit.start(env, addon_name)

    conduit.ecs_exec_is_available_fn.assert_called_once_with(
        ecs_client,
        "arn:aws:ecs:eu-west-2:123456789012:cluster/MyECSCluster1",
        ["arn:aws:ecs:eu-west-2:123456789012:task/MyTaskARN"],
    )
