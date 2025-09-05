import click

from dbt_platform_helper.domain.update_alb_rules import UpdateALBRules
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup)
def internal():
    """Commands for internal platform use."""
    PlatformHelperVersioning().check_if_needs_update()


@internal.group(cls=ClickDocOptGroup)
def alb():
    """Load Balancer related commands."""
    PlatformHelperVersioning().check_if_needs_update()


@alb.command()
@click.option("--env", type=str, required=True)
def update(env: str):
    """Udpate alb rules."""
    try:
        session = get_aws_session_or_abort()
        update_aws = UpdateALBRules(session)
        update_aws.update_alb_rules(environment=env)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
