import subprocess
from collections.abc import Callable

import click

from dbt_platform_helper.providers.cloudformation import CloudFormation
from dbt_platform_helper.providers.copilot import connect_to_addon_client_task
from dbt_platform_helper.providers.copilot import create_addon_client_task
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.providers.secrets import Secrets
from dbt_platform_helper.utils.application import Application


class Conduit:
    def __init__(
        self,
        application: Application,
        secrets_provider: Secrets,
        cloudformation_provider: CloudFormation,
        ecs_provider: ECS,
        echo: Callable[[str], str] = click.secho,
        subprocess: subprocess = subprocess,
        connect_to_addon_client_task=connect_to_addon_client_task,
        create_addon_client_task=create_addon_client_task,
    ):

        self.application = application
        self.secrets_provider = secrets_provider
        self.cloudformation_provider = cloudformation_provider
        self.ecs_provider = ecs_provider
        self.subprocess = subprocess
        self.echo = echo
        self.connect_to_addon_client_task = connect_to_addon_client_task
        self.create_addon_client_task = create_addon_client_task

    def start(self, env: str, addon_name: str, access: str = "read"):
        clients = self._initialise_clients(env)
        addon_type, cluster_arn, parameter_name, task_name = self._get_addon_details(
            addon_name, access
        )

        self.echo(f"Checking if a conduit task is already running for {addon_type}")
        task_arns = self.ecs_provider.get_ecs_task_arns(cluster_arn, task_name)
        if not task_arns:
            self.echo("Creating conduit task")
            self.create_addon_client_task(
                clients["iam"],
                clients["ssm"],
                self.subprocess,
                self.application,
                env,
                addon_type,
                addon_name,
                task_name,
                access,
            )

            self.echo("Updating conduit task")
            self._update_stack_resources(
                self.application.name,
                env,
                addon_type,
                addon_name,
                task_name,
                parameter_name,
                access,
            )

            task_arns = self.ecs_provider.get_ecs_task_arns(cluster_arn, task_name)

        else:
            self.echo("Conduit task already running")

        self.echo(f"Checking if exec is available for conduit task...")

        self.ecs_provider.ecs_exec_is_available(cluster_arn, task_arns)

        self.echo("Connecting to conduit task")
        self.connect_to_addon_client_task(
            clients["ecs"], self.subprocess, self.application.name, env, cluster_arn, task_name
        )

    def _initialise_clients(self, env):
        return {
            "ecs": self.application.environments[env].session.client("ecs"),
            "iam": self.application.environments[env].session.client("iam"),
            "ssm": self.application.environments[env].session.client("ssm"),
        }

    def _get_addon_details(self, addon_name, access):
        addon_type = self.secrets_provider.get_addon_type(addon_name)
        cluster_arn = self.ecs_provider.get_cluster_arn()
        parameter_name = self.secrets_provider.get_parameter_name(addon_type, addon_name, access)
        task_name = self.ecs_provider.get_or_create_task_name(addon_name, parameter_name)

        return addon_type, cluster_arn, parameter_name, task_name

    def _update_stack_resources(
        self,
        app_name,
        env,
        addon_type,
        addon_name,
        task_name,
        parameter_name,
        access,
    ):
        self.cloudformation_provider.add_stack_delete_policy_to_task_role(task_name)
        stack_name = self.cloudformation_provider.update_conduit_stack_resources(
            app_name,
            env,
            addon_type,
            addon_name,
            task_name,
            parameter_name,
            access,
        )
        self.echo("Waiting for conduit task update to complete...")
        self.cloudformation_provider.wait_for_cloudformation_to_reach_status(
            "stack_update_complete", stack_name
        )
