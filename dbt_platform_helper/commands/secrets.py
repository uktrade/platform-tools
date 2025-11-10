#!/usr/bin/env python

from pathlib import Path

import click
from botocore.exceptions import ClientError

from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.utils.application import get_application_name
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.aws import get_ssm_secrets
from dbt_platform_helper.utils.aws import set_ssm_param
from dbt_platform_helper.utils.click import ClickDocOptGroup


def secret_should_be_skipped(secret_name):
    return "AWS_" in secret_name


@click.group(chain=True, cls=ClickDocOptGroup)
def secrets():
    PlatformHelperVersioning().check_if_needs_update()


@secrets.command()
@click.argument("source_environment")
@click.argument("target_environment")
@click.option("--project-profile", required=True, help="AWS account profile name")
def copy(project_profile, source_environment, target_environment):
    """Copy secrets from one environment to a new environment."""
    get_aws_session_or_abort(project_profile)

    if not Path(f"copilot/environments/{target_environment}").exists():
        click.echo(f"""Target environment manifest for "{target_environment}" does not exist.""")
        exit(1)

    app_name = get_application_name()
    secrets = get_ssm_secrets(app_name, source_environment)

    for secret in secrets:
        secret_name = secret[0].replace(f"/{source_environment}/", f"/{target_environment}/")

        if secret_should_be_skipped(secret_name):
            continue

        click.echo(secret_name)

        try:
            set_ssm_param(
                app_name,
                target_environment,
                secret_name,
                secret[1],
                False,
                False,
                f"Copied from {source_environment} environment.",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ParameterAlreadyExists":
                click.secho(
                    f"""The "{secret_name.split("/")[-1]}" parameter already exists for the "{target_environment}" environment.""",
                    fg="yellow",
                )
            else:
                raise e


@secrets.command()
@click.argument("app", type=str, required=True)
@click.argument("env", type=str, required=True)
def list(app, env):
    """[DELETED] List secret names and values for an environment."""

    click.secho(
        message="\nThis command has been removed due to security reasons. To view secrets, log into your AWS account and head over to AWS Parameter Store https://eu-west-2.console.aws.amazon.com/systems-manager/parameters/\n",
        fg="magenta",
    )


if __name__ == "__main__":
    secrets()
