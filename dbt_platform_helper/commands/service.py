import click

from dbt_platform_helper.domain.service import ServiceManager
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup)
def service():
    """Commands for managing a live service."""


@service.command()
@click.option("--app", help="Application name", required=True)
@click.option("--env", help="Environment name", required=True)
@click.option("--service", help="Service name", required=True)
def exec(app: str, env: str, service: str):
    """Opens a shell for a given container."""
    application = load_application(app=app, env=env)

    try:
        ecs_provider: ECS = ECS(
            application.environments[env].session.client("ecs"),
            None,
            application.name,
            env,
        )

        ServiceManager(ecs_provider=ecs_provider).service_exec(app, env, service)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
