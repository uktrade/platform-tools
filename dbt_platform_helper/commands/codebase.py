import json
import os

import click
from boto3 import Session

from dbt_platform_helper.domain.codebase import Codebase
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import ApplicationNotFoundError
from dbt_platform_helper.utils.application import load_application
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
    Codebase().prepare()


@codebase.command()
@click.option("--app", help="AWS application name", required=True)
@click.option(
    "--with-images",
    help="List up to the last 10 images tagged for this codebase",
    default=False,
    is_flag=True,
)
def list(app, with_images):
    Codebase().list(app, with_images)


@codebase.command()
@click.option("--app", help="AWS application name", required=True)
@click.option(
    "--codebase", help="The codebase name as specified in the pipelines.yml file", required=True
)
@click.option("--commit", help="GitHub commit hash", required=True)
def build(app, codebase, commit):
    Codebase().build(app, codebase, commit)


@codebase.command()
@click.option("--app", help="AWS application name", required=True)
@click.option("--env", help="AWS Copilot environment", required=True)
@click.option(
    "--codebase", help="The codebase name as specified in the pipelines.yml file", required=True
)
@click.option("--commit", help="GitHub commit hash", required=True)
def deploy(app, env, codebase, commit):
    Codebase().deploy(app, env, codebase, commit)


def load_application_or_abort(session: Session, app: str) -> Application:
    try:
        return load_application(app, default_session=session)
    except ApplicationNotFoundError:
        click.secho(
            f"""The account "{os.environ.get("AWS_PROFILE")}" does not contain the application "{app}"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
            fg="red",
        )
        raise click.Abort


def check_image_exists(session: Session, application: Application, codebase: str, commit: str):
    ecr_client = session.client("ecr")
    try:
        ecr_client.describe_images(
            repositoryName=f"{application.name}/{codebase}",
            imageIds=[{"imageTag": f"commit-{commit}"}],
        )
    except ecr_client.exceptions.RepositoryNotFoundException:
        click.secho(
            f'The ECR Repository for codebase "{codebase}" does not exist.',
            fg="red",
        )
        raise click.Abort
    except ecr_client.exceptions.ImageNotFoundException:
        click.secho(
            f'The commit hash "{commit}" has not been built into an image, try the '
            "`platform-helper codebase build` command first.",
            fg="red",
        )
        raise click.Abort


def check_codebase_exists(session: Session, application: Application, codebase: str):
    ssm_client = session.client("ssm")
    try:
        parameter = ssm_client.get_parameter(
            Name=f"/copilot/applications/{application.name}/codebases/{codebase}"
        )
        value = parameter["Parameter"]["Value"]
        json.loads(value)
    except (KeyError, ValueError, json.JSONDecodeError, ssm_client.exceptions.ParameterNotFound):
        click.secho(
            f"""The codebase "{codebase}" either does not exist or has not been deployed.""",
            fg="red",
        )
        raise click.Abort


def load_application_with_environment(session: Session, app, env):
    application = load_application_or_abort(session, app)

    if not application.environments.get(env):
        click.secho(
            f"""The environment "{env}" either does not exist or has not been deployed.""",
            fg="red",
        )
        raise click.Abort
    return application


def get_build_url_from_arn(build_arn: str) -> str:
    _, _, _, region, account_id, project_name, build_id = build_arn.split(":")
    project_name = project_name.removeprefix("build/")
    return (
        f"https://eu-west-2.console.aws.amazon.com/codesuite/codebuild/{account_id}/projects/"
        f"{project_name}/build/{project_name}%3A{build_id}"
    )


def start_build_with_confirmation(codebuild_client, confirmation_message, build_options):
    if click.confirm(confirmation_message):
        response = codebuild_client.start_build(**build_options)
        return get_build_url_from_arn(response["build"]["arn"])
