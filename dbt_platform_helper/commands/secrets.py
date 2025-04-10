#!/usr/bin/env python

from pathlib import Path

import click
from botocore.exceptions import ClientError
from cloudfoundry_client.client import CloudFoundryClient

from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.utils.application import get_application_name
from dbt_platform_helper.utils.aws import SSM_BASE_PATH
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.aws import get_ssm_secrets
from dbt_platform_helper.utils.aws import set_ssm_param
from dbt_platform_helper.utils.click import ClickDocOptGroup


def secret_should_be_skipped(secret_name):
    return "AWS_" in secret_name


def get_paas_env_vars(client: CloudFoundryClient, paas: str) -> dict:
    org, space, app = paas.split("/")

    env_vars = None

    for paas_org in client.v2.organizations:
        if paas_org["entity"]["name"] == org:
            for paas_space in paas_org.spaces():
                if paas_space["entity"]["name"] == space:
                    for paas_app in paas_space.apps():
                        if paas_app["entity"]["name"] == app:
                            env_vars = paas_app["entity"]["environment_json"]

    if not env_vars:
        raise Exception(f"Application {paas} not found")

    return dict(env_vars)


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
