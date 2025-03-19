import click

from dbt_platform_helper.domain.codebase import Codebase
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.parameter_store import ParameterStore
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(chain=True, cls=ClickDocOptGroup)
def codebase():
    """Codebase commands."""
    PlatformHelperVersioning().check_if_needs_update()


@codebase.command()
def prepare():
    """Sets up an application codebase for use within a DBT platform project."""
    try:
        Codebase(ParameterStore(get_aws_session_or_abort().client("ssm"))).prepare()
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
        Codebase(ParameterStore(get_aws_session_or_abort().client("ssm"))).list(app, with_images)
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
        Codebase(ParameterStore(get_aws_session_or_abort().client("ssm"))).build(
            app, codebase, commit
        )
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
@click.option(
    "--ref",
    help="AWS ECR image tag, usually in one of the following formats: tag-<image_tag>, commit-<commit_hash> or branch-<branch_name>.",
    required=False,
)
@click.option(
    "--commit",
    help="(DEPRECATED) Use --ref instead to pass the AWS ECR image tag.",
    required=False,
)
def deploy(app: str, env: str, codebase: str, commit: str = None, ref: str = None):

    if commit:
        ClickIOProvider().warn(
            "WARNING: The --commit option is deprecated and will be removed in a future release. Use --ref instead to pass the AWS ECR image tag in the following formats: tag-<image_tag>, commit-<commit_hash> or branch-<branch_name>."
        )

    none_provided = not (commit or ref)
    both_provided = commit and ref
    if none_provided:
        ClickIOProvider().abort_with_error(
            "To deploy, you must provide a --ref option with the AWS ECR image tag in the following formats: tag-<image_tag>, commit-<commit_hash> or branch-<branch_name>."
        )
    elif both_provided:
        ClickIOProvider().abort_with_error(
            "You have provided both --ref and --commit. The latter is deprecated, please supply just --ref."
        )

    try:
        Codebase(ParameterStore(get_aws_session_or_abort().client("ssm"))).deploy(
            app, env, codebase, commit, ref
        )
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
