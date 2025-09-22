import click

from dbt_platform_helper.domain.service import ServiceManager
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.logs import LogsProvider
from dbt_platform_helper.providers.s3 import S3Provider
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
    "--env",
    required=True,
    help="The name of the environment where the ECS service will be created or updated.",
)
@click.option(
    "--image-tag-override",
    required=False,
    help="Custom image tag (overrides containerDefinitions object from S3). Takes precedence over $IMAGE_TAG.",
)
def deploy(name, env, image_tag_override):
    """Register a new ECS task definition from an S3 JSON template, update the
    ECS service, and tail CloudWatch logs until the ECS rollout is complete."""
    click_io = ClickIOProvider()

    try:

        config = ConfigProvider(ConfigValidator()).get_enriched_config()
        application_name = config.get("application", "")
        application = load_application(app=application_name, env=env)

        ecs_client = application.environments[env].session.client("ecs")
        ssm_client = application.environments[env].session.client("ssm")
        s3_client = application.environments[env].session.client("s3")
        logs_client = application.environments[env].session.client("logs")

        ecs_provider = ECS(
            ecs_client=ecs_client,
            ssm_client=ssm_client,
            application_name=application.name,
            env=env,
        )
        s3_provider = S3Provider(client=s3_client)
        logs_provider = LogsProvider(client=logs_client)

        service_manager = ServiceManager(
            ecs_provider=ecs_provider, s3_provider=s3_provider, logs_provider=logs_provider
        )
        service_manager.deploy(
            service=name,
            environment=env,
            application=application.name,
            image_tag_override=image_tag_override,
        )
    except PlatformException as error:
        click_io.abort_with_error(str(error))


@service.command(help="Generate Terraform manifest for the specified service(s).")
@click.option(
    "--name",
    required=False,
    help="The name of the service(s) to generate service manifest(s) for.",
    multiple=True,
)
@click.option(
    "--env",
    required=True,
    help="The name of the environment to generate service manifests for.",
)
@click.option(
    "--image-tag",
    required=False,
    help="Image tag to deploy for the service(s). Takes precedence over the $IMAGE_TAG environment variable.",
)
def generate(name, env, image_tag):
    """Validates the service-config.yml format, applies the environment-specific
    overrides, and generates a Terraform manifest at
    /terraform/services/<environment>/<service>/main.tf.json."""

    services = list(name)
    click_io = ClickIOProvider()

    try:
        service_manager = ServiceManager()
        service_manager.generate(environment=env, services=services, image_tag_flag=image_tag)

    except PlatformException as err:
        click_io.abort_with_error(str(err))
