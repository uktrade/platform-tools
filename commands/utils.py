import re
from pathlib import Path

import boto3
import botocore
import click
import jinja2

SSM_BASE_PATH = "/copilot/{app}/{env}/secrets/"
SSM_PATH = "/copilot/{app}/{env}/secrets/{name}"


def mkdir(base, path):
    if (base / path).exists():
        return f"Directory {path} exists; doing nothing"

    (base / path).mkdir(parents=True)
    return f"Directory {path} created"


def mkfile(base, path, contents, overwrite=False):
    file_exists = (base / path).exists()

    if file_exists and not overwrite:
        return f"File {path} exists; doing nothing"

    action = "overwritten" if overwrite else "created"

    with open(base / path, "w") as fd:
        fd.write(contents)

    return f"File {path} {action}"


def camel_case(s):
    s = re.sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return "".join([s[0].lower(), s[1:]])


def set_ssm_param(app, env, param_name, param_value, overwrite, exists, description="Copied from Cloud Foundry."):
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

    if overwrite and exists:
        # Tags can't be updated when overwriting
        del args["Tags"]

    client.put_parameter(**args)


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


def setup_templates():
    Path(__file__).parent.parent / Path("templates")
    templateLoader = jinja2.PackageLoader("commands")
    templateEnv = jinja2.Environment(loader=templateLoader, keep_trailing_newline=True)

    templates = {
        "instructions": templateEnv.get_template("instructions.txt"),
        "storage-instructions": templateEnv.get_template("storage-instructions.txt"),
        "svc": {
            "public-manifest": templateEnv.get_template("svc/manifest-public.yml"),
            "backend-manifest": templateEnv.get_template("svc/manifest-backend.yml"),
            "s3-policy": templateEnv.get_template("addons/svc/s3-policy.yml"),
        },
        "env": {
            "manifest": templateEnv.get_template("env/manifest.yml"),
            "opensearch": templateEnv.get_template("addons/env/opensearch.yml"),
            "rds-postgres": templateEnv.get_template("addons/env/rds-postgres.yml"),
            "aurora-postgres": templateEnv.get_template("addons/env/aurora-postgres.yml"),
            "redis": templateEnv.get_template("addons/env/redis-cluster.yml"),
            "s3": templateEnv.get_template("addons/env/s3.yml"),
            "parameters": templateEnv.get_template("addons/env/addons.parameters.yml"),
        },
        "docs": templateEnv.get_template("COMMANDS.md.jinja"),
    }

    return templates


def ensure_cwd_is_repo_root():
    """Exit if we're not in the root of the repo."""

    if not Path("./copilot").exists() or not Path("./copilot").is_dir():
        click.secho(
            "Cannot find copilot directory. Run this command in the root of the deployment repository.",
            bg="red",
        )
        exit(1)


def check_aws_conn(aws_profile: str) -> boto3.session.Session:
    # Check that the aws profile exists and is set.
    click.secho("Checking AWS connection...", fg="cyan")

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
    click.echo(
        click.style(f"Logged in with AWS account: ", fg="yellow")
        + click.style(f"{account_name[0]}/{sts.get_caller_identity()['Account']}", fg="white", bold=True),
    )
    click.echo(
        click.style(f"User: ", fg="yellow")
        + click.style(f"{(sts.get_caller_identity()['UserId']).split(':')[-1]}", fg="white", bold=True),
    )

    return session


def check_response(response):
    if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
        click.secho(
            f"Unknown response error from AWS.\nStatus Code: {response['ResponseMetadata']['HTTPStatusCode']}",
            fg="red",
        )
        exit()
