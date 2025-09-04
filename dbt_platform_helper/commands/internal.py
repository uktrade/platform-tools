import click

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.schema_migrations.schema_v1_to_v2_migration import (
    SchemaV1ToV2Migration,
)
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup)
def internal():
    """Internal commands for use within pipelines or by Platform Team."""


@internal.command()
@click.option("--name", required=True, help="The name of the ECS service to create or update.")
@click.option(
    "--environment",
    required=True,
    help="The name of the environment to create or update an ECS service to.",
)
def migrate_manifests(name, environment):
    """Create or update an ECS service."""
    click_io = ClickIOProvider()

    try:

        config = ConfigProvider(ConfigValidator()).get_enriched_config()
        SchemaV1ToV2Migration.migrate(config)
    except PlatformException as error:
        click_io.abort_with_error(str(error))
