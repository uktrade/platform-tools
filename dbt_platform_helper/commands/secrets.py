#!/usr/bin/env python


import click

from dbt_platform_helper.domain.secrets import Secrets
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.aws import SSM_BASE_PATH
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
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
@click.argument("source_environment")
@click.argument("target_environment")
@click.option("--app", help="Application name.", required=True)
def copy(source_environment, target_environment, app):
    """Copy secrets from one environment to a new environment."""

    try:
        Secrets().copy(app, source_environment, target_environment)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))


@secrets.command()
@click.argument("app", type=str, required=True)
@click.argument("env", type=str, required=True)
def list(app, env):
    """List secret names and values for an environment."""

    session = get_aws_session_or_abort()
    client = session.client("ssm")

    path = SSM_BASE_PATH.format(app=app, env=env)

    params = dict(Path=path, Recursive=False, WithDecryption=True, MaxResults=10)
    secrets = []

    while True:
        response = client.get_parameters_by_path(**params)

        for secret in response["Parameters"]:
            secrets.append(f"{secret['Name']:<8}: {secret['Value']:<15}")

        if "NextToken" in response:
            params["NextToken"] = response["NextToken"]
        else:
            break

    # TODO: DBTP-1953: When we refactor this, the above could probably just use dbt_platform_helper.utils.aws.get_ssm_secret_names so we would end up with print("\n".join(get_ssm_secret_names(app, env)))
    print("\n".join(sorted(secrets)))


if __name__ == "__main__":
    secrets()
