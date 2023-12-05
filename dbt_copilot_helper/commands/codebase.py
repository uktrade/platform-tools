import json
import os
import stat
import subprocess
from pathlib import Path

import boto3
import click
import requests
import yaml

from dbt_copilot_helper.utils.application import ApplicationNotFoundError
from dbt_copilot_helper.utils.application import load_application
from dbt_copilot_helper.utils.click import ClickDocOptGroup
from dbt_copilot_helper.utils.files import mkfile
from dbt_copilot_helper.utils.template import setup_templates
from dbt_copilot_helper.utils.versioning import (
    check_copilot_helper_version_needs_update,
)


@click.group(chain=True, cls=ClickDocOptGroup)
def codebase():
    """Codebase commands."""
    check_copilot_helper_version_needs_update()


@codebase.command()
def prepare():
    """Sets up an application codebase for use within a DBT platform project."""
    templates = setup_templates()

    repository = (
        subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
        .stdout.split("/")[-1]
        .strip()
        .removesuffix(".git")
    )

    if repository.endswith("-deploy") or Path("./copilot").exists():
        click.secho(
            "You are in the deploy repository; make sure you are in the application codebase repository.",
            fg="red",
        )
        exit(1)

    builder_configuration_url = "https://raw.githubusercontent.com/uktrade/ci-image-builder/main/image_builder/configuration/builder_configuration.yml"
    builder_configuration_response = requests.get(builder_configuration_url)
    builder_configuration_content = yaml.safe_load(
        builder_configuration_response.content.decode("utf-8")
    )
    builder_versions = next(
        (
            item
            for item in builder_configuration_content["builders"]
            if item["name"] == "paketobuildpacks/builder-jammy-base"
        ),
        None,
    )
    builder_version = max(x["version"] for x in builder_versions["versions"])

    Path("./.copilot/phases").mkdir(parents=True, exist_ok=True)
    image_build_run_contents = templates.get_template(f".copilot/image_build_run.sh").render()

    config_contents = templates.get_template(f".copilot/config.yml").render(
        repository=repository, builder_version=builder_version
    )

    click.echo(
        mkfile(Path("."), ".copilot/image_build_run.sh", image_build_run_contents, overwrite=True)
    )

    image_build_run_file = Path(".copilot/image_build_run.sh")
    image_build_run_file.chmod(image_build_run_file.stat().st_mode | stat.S_IEXEC)

    click.echo(mkfile(Path("."), ".copilot/config.yml", config_contents, overwrite=True))

    for phase in ["build", "install", "post_build", "pre_build"]:
        phase_contents = templates.get_template(f".copilot/phases/{phase}.sh").render()

        click.echo(mkfile(Path("./.copilot"), f"phases/{phase}.sh", phase_contents, overwrite=True))


@codebase.command()
@click.option("--app", help="AWS application name", required=True)
@click.option("--codebase", help="GitHub codebase name", required=True)
@click.option("--commit", help="GitHub commit hash", required=True)
def build(app, codebase, commit):
    """Trigger a CodePipeline pipeline based build."""

    try:
        load_application(app)
    except ApplicationNotFoundError:
        click.secho(
            f"""The account "{os.environ.get("AWS_PROFILE")}" does not contain the application "{app}"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
            fg="red",
        )
        raise click.Abort

    check_if_commit_exists = subprocess.run(
        ["git", "branch", "-r", "--contains", f"{commit}"], capture_output=True, text=True
    )

    if check_if_commit_exists.stderr:
        click.secho(
            f"""The commit hash "{commit}" either does not exist or you need to run `git fetch`.""",
            fg="red",
        )
        raise click.Abort

    codebuild_client = boto3.client("codebuild")
    build_url = start_build_with_confirmation(
        codebuild_client,
        f'You are about to build "{app}" for "{codebase}" with commit "{commit}". Do you want to continue?',
        {
            "projectName": f"codebuild-{app}-{codebase}",
            "artifactsOverride": {"type": "NO_ARTIFACTS"},
            "sourceVersion": commit,
        },
    )

    if build_url:
        return click.echo(
            "Your build has been triggered. Check your build progress in the AWS Console: "
            f"{build_url}",
        )

    return click.echo("Your build was not triggered.")


@codebase.command()
@click.option("--app", help="AWS application name", required=True)
@click.option("--env", help="AWS Copilot environment", required=True)
@click.option("--codebase", help="GitHub codebase name", required=True)
@click.option("--commit", help="GitHub commit hash", required=True)
def deploy(app, env, codebase, commit):
    """Trigger a CodePipeline pipeline based deployment."""
    try:
        application = load_application(app)
    except ApplicationNotFoundError:
        click.secho(
            f"""The account "{os.environ.get("AWS_PROFILE")}" does not contain the application "{app}"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
            fg="red",
        )
        raise click.Abort

    if not application.environments.get(env):
        click.secho(
            f"""The environment "{env}" either does not exist or has not been deployed.""",
            fg="red",
        )
        raise click.Abort

    ssm_client = boto3.client("ssm")
    try:
        codebase_configuration = json.loads(
            ssm_client.get_parameter(
                Name=f"/copilot/applications/{application.name}/codebases/{codebase}",
            )["Parameter"]["Value"]
        )
    except (KeyError, ValueError, json.JSONDecodeError, ssm_client.exceptions.ParameterNotFound):
        click.secho(
            f"""The codebase "{codebase}" either does not exist or has not been deployed.""",
            fg="red",
        )
        raise click.Abort

    ecr_client = boto3.client("ecr")
    try:
        ecr_client.describe_images(
            repositoryName=f"{application.name}/{codebase_configuration['name']}",
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
            "`copilot-helper codebase build` command first.",
            fg="red",
        )
        raise click.Abort

    codebuild_client = boto3.client("codebuild")
    build_url = start_build_with_confirmation(
        codebuild_client,
        f'You are about to deploy "{app}" for "{codebase}" with commit "{commit}" to the "{env}" environment. Do you want to continue?',
        {
            "projectName": f"pipeline-{application.name}-{codebase}-BuildProject",
            "artifactsOverride": {"type": "NO_ARTIFACTS"},
            "sourceTypeOverride": "NO_SOURCE",
            "environmentVariablesOverride": [
                {"name": "COPILOT_ENVIRONMENT", "value": env},
                {"name": "IMAGE_TAG", "value": f"commit-{commit}"},
            ],
        },
    )

    if build_url:
        return click.echo(
            "Your deployment has been triggered. Check your build progress in the AWS Console: "
            f"{build_url}",
        )

    return click.echo("Your deployment was not triggered.")


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
