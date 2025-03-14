import click

from dbt_platform_helper.domain.codebase import Codebase
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(chain=True, cls=ClickDocOptGroup)
def codebase():
    """Codebase commands."""
    PlatformHelperVersioning().check_if_needs_update()


@codebase.command()
def prepare():
    """Sets up an application codebase for use within a DBT platform project."""
    try:
        Codebase().prepare()
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
        Codebase().list(app, with_images)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))


def build_image_reference(commit = None, tag = None, branch = None):
    reference_options = sum([bool(commit), bool(tag), bool(branch)])
    if reference_options != 1:
        ClickIOProvider().abort_with_error(
            "One of --commit, --tag, or --branch must be specified"
        )
    image_reference = None
    if commit:
        image_reference = f"commit-{commit}"
    elif tag:
        image_reference = f"tag-{tag}"
    elif branch:
        image_reference = f"branch-{branch}"

    assert image_reference is not None
    return image_reference


@codebase.command()
@click.option("--app", help="AWS application name", required=True)
@click.option(
    "--codebase",
    help="The codebase name as specified in the platform-config.yml file. This must be run from your codebase repository directory.",
    required=True,
)
@click.option("--commit", help="GitHub commit hash", required=False)
@click.option("--tag", help="GitHub tag", required=False)
@click.option("--branch", help="GitHub branch", required=False)
def build(app, codebase, commit= None, tag = None, branch = None):
    """Trigger a CodePipeline pipeline based build."""
    image_reference = build_image_reference(commit, tag, branch)

    try:
        Codebase().build(app, codebase, image_reference)
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
@click.option("--commit", help="GitHub commit hash", required=False)
@click.option("--tag", help="GitHub tag", required=False)
@click.option("--branch", help="GitHub branch", required=False)
def deploy(app, env, codebase, commit= None, tag = None, branch = None):
    """Trigger a CodePipeline pipeline based deploy."""
    image_reference = build_image_reference(commit, tag, branch)

    try:
        Codebase().deploy(app, env, codebase, image_reference)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
