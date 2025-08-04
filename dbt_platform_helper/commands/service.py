import click

from dbt_platform_helper.domain.service import ServiceManager
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup)
def service():
    """Commands affecting services."""
    PlatformHelperVersioning().check_if_needs_update()


@service.command(help="Generate terraform manifest for the specified service(s).")
@click.option(
    "--name",
    "-n",
    required=False,
    help="The name of the service to generate a manifest for. Multiple values accepted.",
    multiple=True,
)
@click.option(
    "--environment",
    "-e",
    required=False,
    multiple=True,
    help="The name of the environment to generate service manifests for. Multiple values accepted.",
)
@click.option(
    "--image-tag",
    "-i",
    required=False,
    help="Docker image tag to deploy for the service. Overrides the $IMAGE_TAG environment variable.",
)
def generate(name, environment, image_tag):
    """Validates the service-config.yml format, applies the environment-specific
    overrides, and generates a Terraform manifest at
    /terraform/services/<environment>/<service>/main.tf.json."""

    services = list(name)
    environments = list(environment)
    click_io = ClickIOProvider()

    try:
        service_manager = ServiceManager()
        service_manager.generate(
            environments=environments, services=services, image_tag_flag=image_tag
        )

    except PlatformException as err:
        click_io.abort_with_error(str(err))
