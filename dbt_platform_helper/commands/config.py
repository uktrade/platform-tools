import click

from dbt_platform_helper.domain.config import Config
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.aws.sso_auth import SSOAuthProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup)
def config():
    """Perform actions on configuration files."""


@config.command()
def validate():
    """Validate deployment or application configuration."""
    try:
        Config().validate()
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))


@config.command()
def migrate():
    """Update configuration to match current schema."""
    try:
        Config().migrate()
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))


@config.command()
@click.option("--file-path", "-fp", default="~/.aws/config")
def aws(file_path):
    """
    Writes a local config file containing all the AWS profiles to which the
    logged in user has access.

    If no `--file-path` is specified, defaults to `~/.aws/config`.
    """
    try:
        session = get_aws_session_or_abort()
        Config(sso=SSOAuthProvider(session)).generate_aws(file_path)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
