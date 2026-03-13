import click

from dbt_platform_helper.domain.service import ServiceManager
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.application import (
    ApplicationEnvironmentNotFoundException,
)
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup)
def service():
    """Commands for managing a live service."""


@service.command()
@click.option("--app", "-a", help="Application name", required=True)
@click.option("--env", "-e", help="Environment name", required=True)
@click.option("--name", "-n", help="Name of the service", required=True)
@click.option(
    "--command",
    "-c",
    help="Optional. The command that is passed to a running container. (default '/bin/bash')",
    required=False,
)
@click.option(
    "--container",
    help="Optional. The specific container you want to exec in. By default the first essential container will be used.",
    required=False,
)
@click.option("--task-id", help="Optional. ID of the task you want to exec in.", required=False)
def exec(app: str, env: str, name: str, command: str, container: str, task_id: str):
    """Opens a shell for a given container."""

    try:
        application = load_application(app=app, env=env)

        # TODO This is a workaround until DBTP-2754 is fixed
        try:
            ecs_client = application.environments[env].session.client("ecs")
        except KeyError:
            raise ApplicationEnvironmentNotFoundException(app, env)

        ecs_provider: ECS = ECS(
            ecs_client,
            None,
            application.name,
            env,
        )

        ServiceManager(ecs_provider=ecs_provider).service_exec(
            app, env, name, command, container, task_id
        )
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
