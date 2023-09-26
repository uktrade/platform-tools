import boto3
import botocore
import click

from dbt_copilot_helper.exceptions import ValidationException

SSM_BASE_PATH = "/copilot/{app}/{env}/secrets/"
SSM_PATH = "/copilot/{app}/{env}/secrets/{name}"


def check_aws_conn(aws_profile: str) -> boto3.session.Session:
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
    try:
        sts.get_caller_identity()
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
            + click.style(
                f"{account_name[0]}/{sts.get_caller_identity()['Account']}", fg="white", bold=True
            ),
        )
    else:
        click.echo(
            click.style("Logged in with AWS account id: ", fg="yellow")
            + click.style(f"{sts.get_caller_identity()['Account']}", fg="white", bold=True),
        )
    click.echo(
        click.style("User: ", fg="yellow")
        + click.style(
            f"{(sts.get_caller_identity()['UserId']).split(':')[-1]}\n", fg="white", bold=True
        ),
    )

    return session


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
