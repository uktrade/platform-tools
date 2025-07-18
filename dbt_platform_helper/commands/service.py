import click

from dbt_platform_helper.domain.service import ServiceManger
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigLoader
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.click import ClickDocOptGroup

AVAILABLE_TEMPLATES = ["default", "migration", "dmas-migration"]


@click.group(cls=ClickDocOptGroup)
def service():
    """Commands affecting environments."""
    PlatformHelperVersioning().check_if_needs_update()


@service.command(help="Generate terraform manifest for the specified environment.")
@click.option(
    "--name",
    "-n",
    required=False,
    help="The name of the service to generate a manifest for. Multiple values accepted.",
    multiple=True,
    default=[],
)
@click.option(
    "--environment",
    "-e",
    required=False,
    multiple=True,
    default=[],
    help="The name of the environment to generate service manifests for. Multiple values accepted.",
)
def generate(name, environment):
    """Validates the service-config.yml format, applies the environment-specific
    overrides, and generates a Terraform manifest at
    /terraform/services/<environment>/<service>/main.tf.json."""

    click_io = ClickIOProvider()
    try:
        # TODO QUESTION
        # do we generate all services for an environment or ...
        # do we generate all environments for a service

        # source_dir default = "services"
        # environments_to_generate default = all or cli arg
        # services_to_generate default = all or cli arg
        # both flags mean you can do one service for one environment

        config_provider = ConfigProvider(ConfigValidator())
        service_manager = ServiceManger(
            loader=ConfigLoader(),
            config_provider=config_provider,
        )
        service_manager.generate(["dragos"], ["web"])

    except PlatformException as err:
        click_io.abort_with_error(str(err))
