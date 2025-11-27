#!/usr/bin/env python


import click

from dbt_platform_helper.domain.secrets import Secrets
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.click import ClickDocOptGroup


def secret_should_be_skipped(secret_name):
    return "AWS_" in secret_name


@click.group(chain=True, cls=ClickDocOptGroup)
def secrets():
    PlatformHelperVersioning().check_if_needs_update()


@secrets.command()
@click.option("--app", help="Application name.", required=True)
@click.option("--name", help="Secret name (automatically uppercased).", required=True)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Allows overwriting the value of secrets if they already exist.",
)
def create(app: str, name: str, overwrite: bool):
    """Create a Parameter Store secret for all environments of an
    application."""

    try:
        Secrets().create(app, name, overwrite)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))


@secrets.command()
@click.option("--app", help="Application name.", required=True)
@click.option("--source", help="Source environment where to copy secrets from.", required=True)
@click.option("--target", help="Destination environment where to copy secrets to.", required=True)
def copy(app, source, target):
    """Copy secrets from one environment to another."""

    try:
        Secrets().copy(app, source, target)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))


@secrets.command()
@click.argument("app", type=str, required=True)
@click.argument("env", type=str, required=True)
def list(app, env):
    """[DELETED] List secret names and values for an environment."""

    click.secho(
        message="\nThis command has been removed to prevent accidental exposure of secret values in local terminals and logs. To view secrets, log into your AWS account and head over to AWS Parameter Store https://eu-west-2.console.aws.amazon.com/systems-manager/parameters/\n",
        fg="magenta",
    )


if __name__ == "__main__":
    secrets()
