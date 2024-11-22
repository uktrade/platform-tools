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

# TODO - Some bits being imported twice.
# from dbt_platform_helper.providers.copilot import addon_client_is_running
from dbt_platform_helper.providers.copilot import connect_to_addon_client_task
from dbt_platform_helper.providers.copilot import create_addon_client_task
from dbt_platform_helper.providers.copilot import create_postgres_admin_task
from dbt_platform_helper.providers.ecs import addon_client_is_running
from dbt_platform_helper.providers.ecs import get_cluster_arn
from dbt_platform_helper.providers.ecs import get_or_create_task_name
from dbt_platform_helper.providers.ecs import check_if_ecs_exec_is_availble
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
        check_if_ecs_exec_is_availble_fn=check_if_ecs_exec_is_availble,
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
        self.check_if_ecs_exec_is_availble_fn = check_if_ecs_exec_is_availble
        self.get_cluster_arn_fn = get_cluster_arn_fn
        self.get_parameter_name_fn = get_parameter_name_fn
        self.get_or_create_task_name_fn = get_or_create_task_name_fn
        self.add_stack_delete_policy_to_task_role_fn = add_stack_delete_policy_to_task_role_fn
        self.update_conduit_stack_resources_fn = update_conduit_stack_resources_fn
        self.wait_for_cloudformation_to_reach_status_fn = wait_for_cloudformation_to_reach_status_fn
        """
        Initialise a conduit domain which can be used to spin up a conduit
        instance to connect to a service.

        Args:
            application(Application): an object with the data of the deployed application
            subprocess_fn: inject the subprocess function to call and execute shell commands
            echo_fn: a function to echo messages too
            addon_client_is_running_fn: inject the function which will check if a conduit instance to the addon is running
            connect_to_addon_client_task_fn: inject the function used to connect to the conduit instance,
            create_addon_client_task_fn: inject the function used to create the conduit task to connect too
            create_postgres_admin_task_fn: inject the function used to create the conduit task with admin access to postgres
            get_addon_type_fn=get_addon_type: inject the function used to get the addon type from addon name
            get_cluster_arn_fn: inject the function used to get the cluster arn from the application name and environment
            get_parameter_name_fn: inject the function used to get the parameter name from the application and addon
            get_or_create_task_name_fn: inject the function used to get an existing conduit task or generate a new task
            add_stack_delete_policy_to_task_role_fn: inject the function used to create the delete task permission in cloudformation
            update_conduit_stack_resources_fn: inject the function used to add the conduit instance into the cloudformation stack
            wait_for_cloudformation_to_reach_status_fn: inject waiter function for cloudformation
        """

    def start(self, env: str, addon_name: str, access: str = "read"):
        clients = self._initialise_clients(env)
        addon_type, cluster_arn, parameter_name, task_name = self._get_addon_details(
            env, addon_name, access
        )

        # TODO - we probably want some logs here that makes it exactly clear what is happening. - do we want the line below?
        self.echo_fn(f"Checking if an addon client is already running for {addon_type}, and creating a new task if not")
        self.echo_fn(f"TEMP REMOVEME: Checking if addon client is running for {cluster_arn}, {task_name}")
        if not self.addon_client_is_running_fn(clients["ecs"], cluster_arn, task_name):
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

        # TODO - do we want this?, I think it can be a bit unclear what is happening without it.
        else:
            self.echo_fn("Addon client IS infact already running")

        task_arn = self.addon_client_is_running_fn(clients["ecs"], cluster_arn, task_name)
        self.echo_fn(f"Checking if ECS exec is availble for Conduit task...")
        self.check_if_ecs_exec_is_availble_fn(clients["ecs"], cluster_arn, task_arn)

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
