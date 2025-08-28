import click

from dbt_platform_helper.domain.internal import Internal
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup)
def internal():
    """Internal commands for use within pipelines or by Platform Team."""


@internal.group(cls=ClickDocOptGroup)
def service():
    """Subgroup for 'internal service' commands."""


@service.command()
@click.option("--name", required=True, help="The name of the ECS service to create or update.")
@click.option(
    "--environment",
    required=True,
    help="The name of the environment to create or update an ECS service to.",
)
@click.option(
    "--image-tag",
    "-i",
    required=False,
    help="Docker image tag to deploy for the service. Overrides the $IMAGE_TAG environment variable.",
)
def deploy(name, environment, image_tag):
    """Create or update an ECS service."""
    click_io = ClickIOProvider()

    try:

        config = ConfigProvider(ConfigValidator()).get_enriched_config()
        application_name = config.get("application", "")
        application = load_application(app=application_name, env=environment)

        ecs_client = application.environments[environment].session.client("ecs")
        ssm_client = application.environments[environment].session.client("ssm")
        ecs_provider = ECS(ecs_client, ssm_client, application.name, environment)

        internal = Internal(ecs_provider=ecs_provider)
        internal.deploy(
            service=name, environment=environment, application=application.name, image_tag=image_tag
        )
    except PlatformException as error:
        click_io.abort_with_error(str(error))


@service.command()
@click.option("--name", required=True, help="The name of the ECS service to create or update")
@click.option(
    "--environment",
    required=True,
    help="The name of the environment to create or update an ECS service to.",
)
def delete(name, environment):
    """Delete an ECS service."""
    click_io = ClickIOProvider()

    try:
        config = ConfigProvider(ConfigValidator()).get_enriched_config()
        application_name = config.get("application", "")
        application = load_application(app=application_name, env=environment)

        ecs_client = application.environments[environment].session.client("ecs")
        ssm_client = application.environments[environment].session.client("ssm")
        ecs_provider = ECS(ecs_client, ssm_client, application.name, environment)

        internal = Internal(ecs_provider=ecs_provider)
        internal.delete(service=name, environment=environment, application=application.name)
    except PlatformException as error:
        click_io.abort_with_error(str(error))
