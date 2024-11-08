from dbt_platform_helper.providers.cloudformation import (
    add_stack_delete_policy_to_task_role,
)
from dbt_platform_helper.providers.cloudformation import update_conduit_stack_resources
from dbt_platform_helper.providers.copilot import addon_client_is_running
from dbt_platform_helper.providers.copilot import connect_to_addon_client_task
from dbt_platform_helper.providers.copilot import create_addon_client_task
from dbt_platform_helper.providers.copilot import create_postgres_admin_task
from dbt_platform_helper.providers.copilot import get_cluster_arn
from dbt_platform_helper.providers.copilot import get_or_create_task_name
from dbt_platform_helper.providers.copilot import get_parameter_name
from dbt_platform_helper.providers.subprocess import DBTSubprocess
from dbt_platform_helper.utils.application import Application


class Conduit:
    def __init__(
        self,
        env: str,
        application: Application,
        subprocess: DBTSubprocess = DBTSubprocess(),
        addon_client_is_running_fn=addon_client_is_running,
        connect_to_addon_client_task_fn=connect_to_addon_client_task,
        create_addon_client_task_fn=create_addon_client_task,
        create_postgres_admin_task_fn=create_postgres_admin_task,
        get_cluster_arn_fn=get_cluster_arn,
        get_parameter_name_fn=get_parameter_name,
        get_or_create_task_name_fn=get_or_create_task_name,
        add_stack_delete_policy_to_task_role_fn=add_stack_delete_policy_to_task_role,
        update_conduit_stack_resources_fn=update_conduit_stack_resources,
    ):
        """

        Args:
            application(Application): an object with the data of the deployed application
        """
        self.application = application
        self.subprocess = subprocess
        self.ecs_client = self.application.environments[env].session.client("ecs")
        self.iam_client = self.application.environments[env].session.client("iam")
        self.ssm_client = self.application.environments[env].session.client("ssm")
        self.cloudformation_client = self.application.environments[env].session.client(
            "cloudformation"
        )
        self.secrets_manager_client = self.application.environments[env].session.client(
            "secretsmanager"
        )

        self.addon_client_is_running_fn = addon_client_is_running_fn
        self.connect_to_addon_client_task_fn = connect_to_addon_client_task_fn
        self.create_addon_client_task_fn = create_addon_client_task_fn
        self.create_postgres_admin_task = create_postgres_admin_task_fn
        self.get_cluster_arn_fn = get_cluster_arn_fn
        self.get_parameter_name_fn = get_parameter_name_fn
        self.get_or_create_task_name_fn = get_or_create_task_name_fn
        self.add_stack_delete_policy_to_task_role_fn = add_stack_delete_policy_to_task_role_fn
        self.update_conduit_stack_resources_fn = update_conduit_stack_resources_fn

    def start(self, env: str, addon_name: str, addon_type: str, access: str = "read"):
        """"""

        cluster_arn = self.get_cluster_arn_fn(self.ecs_client, self.application, env)
        parameter_name = self.get_parameter_name_fn(
            self.application.name, env, addon_type, addon_name, access
        )
        task_name = self.get_or_create_task_name_fn(
            self.ssm_client, self.application.name, env, addon_name, parameter_name
        )

        if not self.addon_client_is_running_fn(self.ecs_client, cluster_arn, task_name):
            self.create_addon_client_task_fn(
                self.iam_client,
                self.ssm_client,
                self.secrets_manager_client,
                self.subprocess,
                self.application,
                env,
                addon_type,
                addon_name,
                task_name,
                access,
            )
            self.add_stack_delete_policy_to_task_role_fn(self.cloudformation_client, env, task_name)
            self.update_conduit_stack_resources_fn(
                self.cloudformation_client,
                self.iam_client,
                self.ssm_client,
                self.application.name,
                env,
                addon_type,
                addon_name,
                task_name,
                parameter_name,
                access,
            )

        self.connect_to_addon_client_task_fn(
            self.ecs_client, self.subprocess, self.application.name, env, cluster_arn, task_name
        )


class ConduitError(Exception):
    pass


class CreateTaskTimeoutConduitError(ConduitError):
    pass


class InvalidAddonTypeConduitError(ConduitError):
    def __init__(self, addon_type):
        self.addon_type = addon_type


class NoClusterConduitError(ConduitError):
    pass


class SecretNotFoundConduitError(ConduitError):
    pass


class ParameterNotFoundConduitError(ConduitError):
    pass


class AddonNotFoundConduitError(ConduitError):
    pass
