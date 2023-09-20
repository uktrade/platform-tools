import re
from pathlib import Path

import boto3
import botocore
import click
import jinja2
from click import Argument
from click import Context
from click import HelpFormatter

from dbt_copilot_helper.exceptions import ValidationException
from dbt_copilot_helper.jinja2_tags import VersionTag

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
    templateLoader = jinja2.PackageLoader("dbt_copilot_helper")
    templateEnv = jinja2.Environment(loader=templateLoader, keep_trailing_newline=True)
    templateEnv.add_extension(VersionTag)

    return templateEnv


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


def check_response(response):
    if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
        click.secho(
            f"Unknown response error from AWS.\nStatus Code: {response['ResponseMetadata']['HTTPStatusCode']}",
            fg="red",
        )
        exit()


def format_click_usage(ctx: Context, formatter: HelpFormatter, group: bool = False) -> None:
    help_text = f"Usage: {ctx.command_path} "
    current_line = 0
    indent = len(help_text)

    parameters = list(ctx.command.params)
    parameters.sort(key=lambda p: p.required, reverse=True)
    parameters.sort(key=lambda p: hasattr(p, "is_flag") and p.is_flag)
    parameters.sort(key=lambda p: p.__class__.__name__ == "Option")

    if group:
        command_list = list(ctx.command.commands.keys())

        if len(command_list) == 1:
            help_text += f"{command_list[0]} "
        elif len(command_list) <= 4:
            parameters.insert(0, Argument(["command"], type=click.Choice(command_list)))
        else:
            parameters.insert(0, Argument(["command"]))

    for index, param in enumerate(parameters):
        if param.__class__.__name__ == "Argument":
            if hasattr(param.type, "choices"):
                wrap = "(%s) " if param.required else "[(%s)] "
                help_text += wrap % "|".join(param.type.choices)
            else:
                wrap = "<%s> " if param.required else "[<%s>] "
                help_text += wrap % param.name
        elif param.__class__.__name__ == "Option":
            if (
                parameters[index - 1].__class__.__name__ == "Argument"
                and not help_text.split("\n")[current_line].isspace()
                and len(help_text.split("\n")[current_line]) > 40
            ):
                help_text += "\n" + (" " * indent)
                current_line += 1
            if getattr(param, "is_flag", False):
                wrap = "%s " if param.required else "[%s] "
                options = param.opts
                if getattr(param, "default", None) is None:
                    options += param.secondary_opts
                help_text += wrap % "|".join(options)
            elif hasattr(param.type, "choices"):
                wrap = "%s (%s) " if param.required else "[%s (%s)] "
                help_text += wrap % (param.opts[0], "|".join(param.type.choices))
            else:
                wrap = "%s <%s> " if param.required else "[%s <%s>] "
                help_text += wrap % (param.opts[0], param.name)

        if index + 1 != len(parameters) and len(help_text.split("\n")[current_line]) > 70:
            help_text += "\n" + (" " * indent)
            current_line += 1

    formatter.write(f"{help_text}\n")


class ClickDocOptCommand(click.Command):
    def format_usage(self, ctx: Context, formatter: HelpFormatter) -> None:
        format_click_usage(ctx, formatter)


class ClickDocOptGroup(click.Group):
    command_class = ClickDocOptCommand

    def format_usage(self, ctx: Context, formatter: HelpFormatter) -> None:
        format_click_usage(ctx, formatter, True)
