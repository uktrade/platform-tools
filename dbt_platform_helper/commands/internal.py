import click

from dbt_platform_helper.domain.service import ServiceManager
from dbt_platform_helper.domain.update_alb_rules import UpdateALBRules
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
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
def alb():
    """Load Balancer related commands."""
    PlatformHelperVersioning().check_if_needs_update()


@alb.command()
@click.option("--env", type=str, required=True)
def update_rules(env: str):
    """Update alb rules based on service-deployment-mode for a given
    environment."""
    try:
        session = get_aws_session_or_abort()
        update_aws = UpdateALBRules(session)
        update_aws.update_alb_rules(environment=env)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
