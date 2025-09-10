import click

from dbt_platform_helper.domain.service import ServiceManager
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
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
