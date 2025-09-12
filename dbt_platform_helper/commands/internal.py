import click

from dbt_platform_helper.domain.service import ServiceManager
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


@internal.command()
def migrate_service_manifests():
    """Migrate copilot manifests to service manifests."""
    click_io = ClickIOProvider()

    try:
        service_manager = ServiceManager()
        service_manager.migrate_copilot_manifests()
    except PlatformException as error:
        click_io.abort_with_error(str(error))


@internal.group(cls=ClickDocOptGroup)
def service():
    """Subgroup for 'internal service' commands."""


@service.command(help="Trigger an ECS deployment.")
@click.option("--name", required=True, help="The name of the ECS service to create or update.")
@click.option(
    "--environment",
    required=True,
    help="The name of the environment to create or update an ECS service to.",
)
@click.option(
    "--image-tag-override",
    required=False,
    help="Override the Docker image to be deployed for this service. This flag takes precedence over the $IMAGE_TAG environment variable.",
)
def deploy(name, environment, image_tag_override):
    """Register a new ECS task definition from an S3 JSON template, update the
    ECS service, and tail CloudWatch logs until the ECS rollout is complete."""
    click_io = ClickIOProvider()

    try:

        config = ConfigProvider(ConfigValidator()).get_enriched_config()
        application_name = config.get("application", "")
        application = load_application(app=application_name, env=environment)

        ecs_client = application.environments[environment].session.client("ecs")
        ssm_client = application.environments[environment].session.client("ssm")
        ecs_provider = ECS(ecs_client, ssm_client, application.name, environment)

        service_manager = ServiceManager(ecs_provider=ecs_provider)
        service_manager.deploy(
            service=name,
            environment=environment,
            application=application.name,
            image_tag_override=image_tag_override,
        )
    except PlatformException as error:
        click_io.abort_with_error(str(error))


@service.command(help="Generate Terraform manifest for the specified service(s).")
@click.option(
    "--name",
    required=False,
    help="The name of the service to generate a manifest for. Multiple values accepted.",
    multiple=True,
)
@click.option(
    "--environment",
    required=True,
    help="The name of the environment to generate service manifests for. Multiple values accepted.",
)
@click.option(
    "--image-tag",
    required=False,
    help="Docker image tag to deploy for the service. Overrides the $IMAGE_TAG environment variable.",
)
def generate(name, environment, image_tag):
    """Validates the service-config.yml format, applies the environment-specific
    overrides, and generates a Terraform manifest at
    /terraform/services/<environment>/<service>/main.tf.json."""

    services = list(name)
    click_io = ClickIOProvider()

    try:
        service_manager = ServiceManager()
        service_manager.generate(
            environment=environment, services=services, image_tag_flag=image_tag
        )

    except PlatformException as err:
        click_io.abort_with_error(str(err))
