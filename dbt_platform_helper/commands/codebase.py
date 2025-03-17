import boto3
import click

from dbt_platform_helper.domain.codebase import Codebase
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.parameter_store import ParameterStore
from dbt_platform_helper.utils.click import ClickDocOptGroup

parameter_provider = ParameterStore(boto3.client("ssm"))


@click.group(chain=True, cls=ClickDocOptGroup)
def codebase():
    """Codebase commands."""
    PlatformHelperVersioning().check_if_needs_update()


@codebase.command()
def prepare():
    """Sets up an application codebase for use within a DBT platform project."""
    try:
        Codebase(parameter_provider).prepare()
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))


@codebase.command()
@click.option("--app", help="AWS application name", required=True)
@click.option(
    "--with-images",
    help="List up to the last 10 images tagged for this codebase",
    default=False,
    is_flag=True,
)
def list(app, with_images):
    """List available codebases for the application."""
    try:
        Codebase(parameter_provider).list(app, with_images)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))


@codebase.command()
@click.option("--app", help="AWS application name", required=True)
@click.option(
    "--codebase",
    help="The codebase name as specified in the platform-config.yml file. This must be run from your codebase repository directory.",
    required=True,
)
@click.option("--commit", help="GitHub commit hash", required=True)
def build(app, codebase, commit):
    """Trigger a CodePipeline pipeline based build."""
    try:
        Codebase(parameter_provider).build(app, codebase, commit)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))


@codebase.command()
@click.option("--app", help="AWS application name", required=True)
@click.option("--env", help="AWS Copilot environment", required=True)
@click.option(
    "--codebase",
    help="The codebase name as specified in the platform-config.yml file. This can be run from any directory.",
    required=True,
)
@click.option("--commit", help="GitHub commit hash", required=True)
def deploy(app, env, codebase, commit):
    try:
        Codebase(parameter_provider).deploy(app, env, codebase, commit)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
