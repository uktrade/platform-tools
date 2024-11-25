import subprocess
from collections.abc import Callable

import click

from dbt_platform_helper.providers.cloudformation import (
    add_stack_delete_policy_to_task_role,
)
from dbt_platform_helper.providers.cloudformation import update_conduit_stack_resources
from dbt_platform_helper.providers.cloudformation import (
    wait_for_cloudformation_to_reach_status,
)

from dbt_platform_helper.providers.copilot import connect_to_addon_client_task
from dbt_platform_helper.providers.copilot import create_addon_client_task
from dbt_platform_helper.providers.copilot import create_postgres_admin_task
from dbt_platform_helper.providers.ecs import addon_client_is_running
from dbt_platform_helper.providers.ecs import check_if_ecs_exec_is_available
from dbt_platform_helper.providers.ecs import get_cluster_arn
from dbt_platform_helper.providers.ecs import get_or_create_task_name
from dbt_platform_helper.providers.secrets import get_addon_type
from dbt_platform_helper.providers.secrets import get_parameter_name
from dbt_platform_helper.utils.application import Application


class Conduit:
    def __init__(
        self,
        application: Application,
        echo_fn: Callable[[str], str] = click.secho,
        subprocess_fn: subprocess = subprocess,
        addon_client_is_running_fn=addon_client_is_running,
        connect_to_addon_client_task_fn=connect_to_addon_client_task,
        create_addon_client_task_fn=create_addon_client_task,
        create_postgres_admin_task_fn=create_postgres_admin_task,
        get_addon_type_fn=get_addon_type,
        check_if_ecs_exec_is_available_fn=check_if_ecs_exec_is_available,
        get_cluster_arn_fn=get_cluster_arn,
        get_parameter_name_fn=get_parameter_name,
        get_or_create_task_name_fn=get_or_create_task_name,
        add_stack_delete_policy_to_task_role_fn=add_stack_delete_policy_to_task_role,
        update_conduit_stack_resources_fn=update_conduit_stack_resources,
        wait_for_cloudformation_to_reach_status_fn=wait_for_cloudformation_to_reach_status,
    ):

        self.application = application
        self.subprocess_fn = subprocess_fn
        self.echo_fn = echo_fn
        self.addon_client_is_running_fn = addon_client_is_running_fn
        self.connect_to_addon_client_task_fn = connect_to_addon_client_task_fn
        self.create_addon_client_task_fn = create_addon_client_task_fn
        self.create_postgres_admin_task = create_postgres_admin_task_fn
        self.get_addon_type_fn = get_addon_type_fn
        self.check_if_ecs_exec_is_available_fn = check_if_ecs_exec_is_available_fn
        self.get_cluster_arn_fn = get_cluster_arn_fn
        self.get_parameter_name_fn = get_parameter_name_fn
        self.get_or_create_task_name_fn = get_or_create_task_name_fn
        self.add_stack_delete_policy_to_task_role_fn = add_stack_delete_policy_to_task_role_fn
        self.update_conduit_stack_resources_fn = update_conduit_stack_resources_fn
        self.wait_for_cloudformation_to_reach_status_fn = wait_for_cloudformation_to_reach_status_fn

    def start(self, env: str, addon_name: str, access: str = "read"):
        clients = self._initialise_clients(env)
        addon_type, cluster_arn, parameter_name, task_name = self._get_addon_details(
            env, addon_name, access
        )

        self.echo_fn(f"Checking if a conduit task is already running for {addon_type}")
        task_arn = self.addon_client_is_running_fn(clients["ecs"], cluster_arn, task_name)
        if not task_arn:
            self.echo_fn("Creating conduit task")
            self.create_addon_client_task_fn(
                clients["iam"],
                clients["ssm"],
                clients["secrets_manager"],
                self.subprocess_fn,
                self.application,
                env,
                addon_type,
                addon_name,
                task_name,
                access,
            )

            self.echo_fn("Updating conduit task")
            self._update_stack_resources(
                clients["cloudformation"],
                clients["iam"],
                clients["ssm"],
                self.application.name,
                env,
                addon_type,
                addon_name,
                task_name,
                parameter_name,
                access,
            )

            task_arn = self.addon_client_is_running_fn(clients["ecs"], cluster_arn, task_name)

        else:
            self.echo_fn("Conduit task already running")

        self.echo_fn(f"Checking if exec is available for conduit task...")
        self.check_if_ecs_exec_is_available_fn(clients["ecs"], cluster_arn, task_arn)

        self.echo_fn("Connecting to conduit task")
        self.connect_to_addon_client_task_fn(
            clients["ecs"], self.subprocess_fn, self.application.name, env, cluster_arn, task_name
        )

    def _initialise_clients(self, env):
        return {
            "ecs": self.application.environments[env].session.client("ecs"),
            "iam": self.application.environments[env].session.client("iam"),
            "ssm": self.application.environments[env].session.client("ssm"),
            "cloudformation": self.application.environments[env].session.client("cloudformation"),
            "secrets_manager": self.application.environments[env].session.client("secretsmanager"),
        }

    def _get_addon_details(self, env, addon_name, access):
        ssm_client = self.application.environments[env].session.client("ssm")
        ecs_client = self.application.environments[env].session.client("ecs")

        addon_type = self.get_addon_type_fn(ssm_client, self.application.name, env, addon_name)
        cluster_arn = self.get_cluster_arn_fn(ecs_client, self.application.name, env)
        parameter_name = self.get_parameter_name_fn(
            self.application.name, env, addon_type, addon_name, access
        )
        task_name = self.get_or_create_task_name_fn(
            ssm_client, self.application.name, env, addon_name, parameter_name
        )

        return addon_type, cluster_arn, parameter_name, task_name

    def _update_stack_resources(
        self,
        cloudformation_client,
        iam_client,
        ssm_client,
        app_name,
        env,
        addon_type,
        addon_name,
        task_name,
        parameter_name,
        access,
    ):
        self.add_stack_delete_policy_to_task_role_fn(cloudformation_client, iam_client, task_name)
        stack_name = self.update_conduit_stack_resources_fn(
            cloudformation_client,
            iam_client,
            ssm_client,
            app_name,
            env,
            addon_type,
            addon_name,
            task_name,
            parameter_name,
            access,
        )
        self.echo_fn("Waiting for conduit task update to complete...")
        self.wait_for_cloudformation_to_reach_status_fn(
            cloudformation_client, "stack_update_complete", stack_name
        )
