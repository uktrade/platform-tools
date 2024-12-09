import click

from dbt_platform_helper.domain.codebase import Codebase
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)


@click.group(chain=True, cls=ClickDocOptGroup)
def codebase():
    """Codebase commands."""
    check_platform_helper_version_needs_update()


@codebase.command()
def prepare():
    """Sets up an application codebase for use within a DBT platform project."""
    try:
        Codebase().prepare()
    except PlatformException as err:
        click.secho(str(err), fg="red")
        raise click.Abort


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
        Codebase().list(app, with_images)
    except PlatformException as err:
        click.secho(str(err), fg="red")
        raise click.Abort


@codebase.command()
@click.option("--app", help="AWS application name", required=True)
@click.option(
    "--codebase",
    help="The codebase name as specified in the platform-config.yml file",
    required=True,
)
@click.option("--commit", help="GitHub commit hash", required=True)
def build(app, codebase, commit):
    """Trigger a CodePipeline pipeline based build."""
    try:
        Codebase().build(app, codebase, commit)
    except PlatformException as err:
        click.secho(str(err), fg="red")
        raise click.Abort


@codebase.command()
@click.option("--app", help="AWS application name", required=True)
@click.option("--env", help="AWS Copilot environment", required=True)
@click.option(
    "--codebase",
    help="The codebase name as specified in the platform-config.yml file",
    required=True,
)
@click.option("--commit", help="GitHub commit hash", required=True)
def deploy(app, env, codebase, commit):
    try:
        Codebase().deploy(app, env, codebase, commit)
    except PlatformException as err:
        click.secho(str(err), fg="red")
        raise click.Abort
