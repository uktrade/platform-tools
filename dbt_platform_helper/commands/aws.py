import click

from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)


@click.group(chain=True, cls=ClickDocOptGroup)
def aws():
    """AWS commands."""
    check_platform_helper_version_needs_update()


@aws.command()
def configure():
    # Todo: doc comment
    get_aws_session_or_abort()
