import json
import os

import click

from dbt_platform_helper.domain.codebase import Codebase
from dbt_platform_helper.exceptions import ApplicationDeploymentNotTriggered
from dbt_platform_helper.exceptions import ApplicationEnvironmentNotFoundError
from dbt_platform_helper.exceptions import ApplicationNotFoundError
from dbt_platform_helper.exceptions import CopilotCodebaseNotFoundError
from dbt_platform_helper.exceptions import ImageNotFoundError
from dbt_platform_helper.exceptions import NoCopilotCodebasesFoundError
from dbt_platform_helper.exceptions import NotInCodeBaseRepositoryError
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.git import CommitNotFoundError
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
    except NotInCodeBaseRepositoryError:
        # TODO print error attached to exception
        click.secho(
            "You are in the deploy repository; make sure you are in the application codebase repository.",
            fg="red",
        )
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
    except NoCopilotCodebasesFoundError:
        click.secho(
            f"""No codebases found for application "{app}""",
            fg="red",
        )
        raise click.Abort
    except ApplicationNotFoundError:
        click.secho(
            f"""The account "{os.environ.get("AWS_PROFILE")}" does not contain the application "{app}"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
            fg="red",
        )
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
    except ApplicationNotFoundError:
        click.secho(
            f"""The account "{os.environ.get("AWS_PROFILE")}" does not contain the application "{app}"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
            fg="red",
        )
        raise click.Abort
    except CommitNotFoundError:
        click.secho(
            f'The commit hash "{commit}" either does not exist or you need to run `git fetch`.',
            fg="red",
        )
        raise click.Abort
    except ApplicationDeploymentNotTriggered:
        click.secho(
            f"Your build for {codebase} was not triggered.",
            fg="red",
        )
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
    except ApplicationNotFoundError:
        click.secho(
            f"""The account "{os.environ.get("AWS_PROFILE")}" does not contain the application "{app}"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
            fg="red",
        )
        raise click.Abort
    except ApplicationEnvironmentNotFoundError:
        click.secho(
            f"""The environment "{env}" either does not exist or has not been deployed.""",
            fg="red",
        )
        raise click.Abort
    # TODO: don't hide json decode error
    except (
        CopilotCodebaseNotFoundError,
        json.JSONDecodeError,
    ):
        click.secho(
            f"""The codebase "{codebase}" either does not exist or has not been deployed.""",
            fg="red",
        )
        raise click.Abort
    except ImageNotFoundError:
        click.secho(
            f'The commit hash "{commit}" has not been built into an image, try the '
            "`platform-helper codebase build` command first.",
            fg="red",
        )
        raise click.Abort
    except ApplicationDeploymentNotTriggered:
        click.secho(
            f"Your deployment for {codebase} was not triggered.",
            fg="red",
        )
        raise click.Abort
