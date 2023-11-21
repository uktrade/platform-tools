import os
from configparser import ConfigParser
from pathlib import Path

import boto3
import botocore
import click

from dbt_copilot_helper.exceptions import ValidationException

SSM_BASE_PATH = "/copilot/{app}/{env}/secrets/"
SSM_PATH = "/copilot/{app}/{env}/secrets/{name}"


def get_aws_session_or_abort(aws_profile: str = None) -> boto3.session.Session:
    aws_profile = aws_profile if aws_profile else os.getenv("AWS_PROFILE")

    # Check that the aws profile exists and is set.
    click.secho(f"""Checking AWS connection for profile "{aws_profile}"...""", fg="cyan")

    try:
        session = boto3.session.Session(profile_name=aws_profile)
    except botocore.exceptions.ProfileNotFound:
        click.secho(f"""AWS profile "{aws_profile}" is not configured.""", fg="red")
        exit()
    except botocore.errorfactory.UnauthorizedException:
        click.secho(
            "The SSO session associated with this profile has expired or is otherwise invalid.  "
            "To refresh this SSO session run aws sso login with the corresponding profile",
            fg="red",
        )
        exit()

    sts = session.client("sts")
    account_id = None
    user_id = None
    try:
        response = sts.get_caller_identity()
        account_id = response["Account"]
        user_id = response["UserId"]
        click.secho("Credentials are valid.", fg="green")
    except botocore.exceptions.SSOTokenLoadError:
        click.secho(
            f"Credentials are NOT valid.  \nPlease login with: aws sso login --profile {aws_profile}",
            fg="red",
        )
        exit()
    except botocore.exceptions.UnauthorizedSSOTokenError:
        click.secho(
            "The SSO session associated with this profile has expired or is otherwise invalid.  "
            "To refresh this SSO session run aws sso login with the corresponding profile",
            fg="red",
        )
        exit()

    alias_client = session.client("iam")
    account_name = alias_client.list_account_aliases()["AccountAliases"]
    if account_name:
        click.echo(
            click.style("Logged in with AWS account: ", fg="yellow")
            + click.style(f"{account_name[0]}/{account_id}", fg="white", bold=True),
        )
    else:
        click.echo(
            click.style("Logged in with AWS account id: ", fg="yellow")
            + click.style(f"{account_id}", fg="white", bold=True),
        )
    click.echo(
        click.style("User: ", fg="yellow")
        + click.style(f"{user_id.split(':')[-1]}\n", fg="white", bold=True),
    )

    return session


class NoProfileForAccountIdError(Exception):
    def __init__(self, account_id):
        super().__init__(f"No profile found for account {account_id}")


def get_profile_name_from_account_id(account_id: str):
    aws_config = ConfigParser()
    aws_config.read(Path.home().joinpath(".aws/config"))
    for section in aws_config.sections():
        found_account_id = aws_config[section].get("sso_account_id", None)
        if account_id == found_account_id:
            return section.removeprefix("profile ")

    raise NoProfileForAccountIdError(account_id)


def get_ssm_secret_names(app, env):
    client = boto3.client("ssm")

    path = SSM_BASE_PATH.format(app=app, env=env)

    params = dict(
        Path=path,
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    secret_names = []

    while True:
        response = client.get_parameters_by_path(**params)

        for secret in response["Parameters"]:
            secret_names.append(secret["Name"])

        if "NextToken" in response:
            params["NextToken"] = response["NextToken"]
        else:
            break

    return sorted(secret_names)


def get_ssm_secrets(app, env):
    """Return secrets from AWS Parameter Store as a list of tuples with the
    secret name and secret value."""

    client = boto3.client("ssm")

    path = SSM_BASE_PATH.format(app=app, env=env)

    params = dict(
        Path=path,
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    secrets = []

    while True:
        response = client.get_parameters_by_path(**params)

        for secret in response["Parameters"]:
            secrets.append((secret["Name"], secret["Value"]))

        if "NextToken" in response:
            params["NextToken"] = response["NextToken"]
        else:
            break

    return sorted(secrets)


def set_ssm_param(
    app, env, param_name, param_value, overwrite, exists, description="Copied from Cloud Foundry."
):
    client = boto3.client("ssm")

    args = dict(
        Name=param_name,
        Description=description,
        Value=param_value,
        Type="SecureString",
        Overwrite=overwrite,
        Tags=[
            {"Key": "copilot-application", "Value": app},
            {"Key": "copilot-environment", "Value": env},
        ],
        Tier="Intelligent-Tiering",
    )

    if overwrite and not exists:
        raise ValidationException(
            """Arguments "overwrite" is set to True, but "exists" is set to False."""
        )

    if overwrite and exists:
        # Tags can't be updated when overwriting
        del args["Tags"]

    client.put_parameter(**args)


def check_response(response):
    if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
        click.secho(
            f"Unknown response error from AWS.\nStatus Code: {response['ResponseMetadata']['HTTPStatusCode']}",
            fg="red",
        )
        exit()


def get_codestar_connection_arn(app_name):
    response = boto3.client("codestar-connections").list_connections()

    for connection in response["Connections"]:
        if connection["ConnectionName"] == app_name:
            return connection["ConnectionArn"]
