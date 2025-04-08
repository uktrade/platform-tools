import json
import os
import time
import urllib.parse
from configparser import ConfigParser
from pathlib import Path

import boto3
import botocore
import botocore.exceptions
import click
from boto3 import Session
from botocore.exceptions import ClientError

from dbt_platform_helper.constants import REFRESH_TOKEN_MESSAGE
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.aws.exceptions import (
    CopilotCodebaseNotFoundException,
)
from dbt_platform_helper.providers.aws.exceptions import LogGroupNotFoundException
from dbt_platform_helper.providers.validation import ValidationException

SSM_BASE_PATH = "/copilot/{app}/{env}/secrets/"
SSM_PATH = "/copilot/{app}/{env}/secrets/{name}"
AWS_SESSION_CACHE = {}


def get_aws_session_or_abort(aws_profile: str = None) -> boto3.session.Session:
    aws_profile = aws_profile or os.getenv("AWS_PROFILE")
    if aws_profile in AWS_SESSION_CACHE:
        return AWS_SESSION_CACHE[aws_profile]

    click.secho(f'Checking AWS connection for profile "{aws_profile}"...', fg="cyan")

    try:
        session = boto3.session.Session(profile_name=aws_profile)
        sts = session.client("sts")
        account_id, user_id = get_account_details(sts)
        click.secho("Credentials are valid.", fg="green")

    except botocore.exceptions.ProfileNotFound:
        _handle_error(f'AWS profile "{aws_profile}" is not configured.')
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "ExpiredToken":
            _handle_error(
                f"Credentials are NOT valid.  \nPlease login with: aws sso login --profile {aws_profile}"
            )
    except botocore.exceptions.NoCredentialsError:
        _handle_error("There are no credentials set for this session.", REFRESH_TOKEN_MESSAGE)
    except botocore.exceptions.UnauthorizedSSOTokenError:
        _handle_error("The SSO Token used for this session is unauthorised.", REFRESH_TOKEN_MESSAGE)
    except botocore.exceptions.TokenRetrievalError:
        _handle_error("Unable to retrieve the Token for this session.", REFRESH_TOKEN_MESSAGE)
    except botocore.exceptions.SSOTokenLoadError:
        _handle_error(
            "The SSO session associated with this profile has expired, is not set or is otherwise invalid.",
            REFRESH_TOKEN_MESSAGE,
        )

    alias_client = session.client("iam")
    account_name = alias_client.list_account_aliases().get("AccountAliases", [])

    _log_account_info(account_name, account_id)

    click.echo(
        click.style("User: ", fg="yellow")
        + click.style(f"{user_id.split(':')[-1]}\n", fg="white", bold=True)
    )

    AWS_SESSION_CACHE[aws_profile] = session
    return session


def _handle_error(message: str, refresh_token_message: str = None) -> None:
    full_message = message + (" " + refresh_token_message if refresh_token_message else "")
    click.secho(full_message, fg="red")
    exit(1)


def _log_account_info(account_name: list, account_id: str) -> None:
    if account_name:
        click.echo(
            click.style("Logged in with AWS account: ", fg="yellow")
            + click.style(f"{account_name[0]}/{account_id}", fg="white", bold=True)
        )
    else:
        click.echo(
            click.style("Logged in with AWS account id: ", fg="yellow")
            + click.style(f"{account_id}", fg="white", bold=True)
        )


class NoProfileForAccountIdException(PlatformException):
    def __init__(self, account_id):
        super().__init__(f"No profile found for account {account_id}")


def get_profile_name_from_account_id(account_id: str):
    aws_config = ConfigParser()
    aws_config.read(Path.home().joinpath(".aws/config"))
    for section in aws_config.sections():
        found_account_id = aws_config[section].get(
            "sso_account_id", aws_config[section].get("profile_account_id", None)
        )
        if account_id == found_account_id:
            return section.removeprefix("profile ")

    raise NoProfileForAccountIdException(account_id)


def get_ssm_secret_names(app, env):
    session = get_aws_session_or_abort()
    client = session.client("ssm")

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


def get_ssm_secrets(app, env, session=None, path=None):
    """Return secrets from AWS Parameter Store as a list of tuples with the
    secret name and secret value."""

    if not session:
        session = get_aws_session_or_abort()
    client = session.client("ssm")

    if not path:
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
    session = get_aws_session_or_abort()
    client = session.client("ssm")

    parameter_args = dict(
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
        del parameter_args["Tags"]

    client.put_parameter(**parameter_args)


def get_codestar_connection_arn(app_name):
    session = get_aws_session_or_abort()
    response = session.client("codestar-connections").list_connections()

    for connection in response["Connections"]:
        if connection["ConnectionName"] == app_name:
            return connection["ConnectionArn"]


def get_account_details(sts_client=None):
    if not sts_client:
        sts_client = get_aws_session_or_abort().client("sts")
    response = sts_client.get_caller_identity()

    return response["Account"], response["UserId"]


def get_postgres_connection_data_updated_with_master_secret(session, parameter_name, secret_arn):
    # TODO: DBTP-1968: This is pretty much the same as dbt_platform_helper.providers.secrets.Secrets.get_postgres_connection_data_updated_with_master_secret
    ssm_client = session.client("ssm")
    secrets_manager_client = session.client("secretsmanager")
    response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
    parameter_value = response["Parameter"]["Value"]

    parameter_data = json.loads(parameter_value)

    secret_response = secrets_manager_client.get_secret_value(SecretId=secret_arn)
    secret_value = json.loads(secret_response["SecretString"])

    parameter_data["username"] = urllib.parse.quote(secret_value["username"])
    parameter_data["password"] = urllib.parse.quote(secret_value["password"])

    return parameter_data


def get_connection_string(
    session: Session,
    app: str,
    env: str,
    db_identifier: str,
    connection_data=get_postgres_connection_data_updated_with_master_secret,
) -> str:
    addon_name = db_identifier.split(f"{app}-{env}-", 1)[1]
    normalised_addon_name = addon_name.replace("-", "_").upper()
    connection_string_parameter = (
        f"/copilot/{app}/{env}/secrets/{normalised_addon_name}_READ_ONLY_USER"
    )
    master_secret_name = f"/copilot/{app}/{env}/secrets/{normalised_addon_name}_RDS_MASTER_ARN"
    master_secret_arn = session.client("ssm").get_parameter(
        Name=master_secret_name, WithDecryption=True
    )["Parameter"]["Value"]

    conn = connection_data(session, connection_string_parameter, master_secret_arn)

    return f"postgres://{conn['username']}:{conn['password']}@{conn['host']}:{conn['port']}/{conn['dbname']}"


def start_build_extraction(codebuild_client, build_options):
    response = codebuild_client.start_build(**build_options)
    return response["build"]["arn"]


def start_pipeline_and_return_execution_id(codepipeline_client, build_options):
    response = codepipeline_client.start_pipeline_execution(**build_options)
    return response["pipelineExecutionId"]


# TODO: DBTP-1888: This should probably be in the AWS Copilot provider
def check_codebase_exists(session: Session, application, codebase: str):
    try:
        # TODO: DBTP-1968: Can this leverage dbt_platform_helper.providers.secrets.Secrets.get_connection_secret_arn?
        ssm_client = session.client("ssm")
        json.loads(
            ssm_client.get_parameter(
                Name=f"/copilot/applications/{application.name}/codebases/{codebase}"
            )["Parameter"]["Value"]
        )
    except (
        KeyError,
        ValueError,
        ssm_client.exceptions.ParameterNotFound,
        json.JSONDecodeError,
    ):
        raise CopilotCodebaseNotFoundException(codebase)


def get_build_url_from_arn(build_arn: str) -> str:
    _, _, _, region, account_id, project_name, build_id = build_arn.split(":")
    project_name = project_name.removeprefix("build/")
    return (
        f"https://eu-west-2.console.aws.amazon.com/codesuite/codebuild/{account_id}/projects/"
        f"{project_name}/build/{project_name}%3A{build_id}"
    )


def get_build_url_from_pipeline_execution_id(execution_id: str, pipeline_name: str) -> str:

    return f"https://eu-west-2.console.aws.amazon.com/codesuite/codepipeline/pipelines/{pipeline_name}/executions/{execution_id}"


def list_latest_images(ecr_client, ecr_repository_name, codebase_repository, echo):
    paginator = ecr_client.get_paginator("describe_images")
    describe_images_response_iterator = paginator.paginate(
        repositoryName=ecr_repository_name,
        filter={"tagStatus": "TAGGED"},
    )
    images = []
    for page in describe_images_response_iterator:
        images += page["imageDetails"]

    sorted_images = sorted(
        images,
        key=lambda i: i["imagePushedAt"],
        reverse=True,
    )

    MAX_RESULTS = 20

    for image in sorted_images[:MAX_RESULTS]:
        try:
            commit_tag = next(t for t in image["imageTags"] if t.startswith("commit-"))
            if not commit_tag:
                continue

            commit_hash = commit_tag.replace("commit-", "")
            echo(
                f"  - https://github.com/{codebase_repository}/commit/{commit_hash} - published: {image['imagePushedAt']}"
            )
        except StopIteration:
            continue


def wait_for_log_group_to_exist(log_client, log_group_name, attempts=30):
    current_attempts = 0
    log_group_exists = False

    while not log_group_exists and current_attempts < attempts:
        current_attempts += 1

        log_group_response = log_client.describe_log_groups(logGroupNamePrefix=log_group_name)
        log_groups = log_group_response.get("logGroups", [])

        for group in log_groups:
            if group["logGroupName"] == log_group_name:
                log_group_exists = True

        time.sleep(1)

    if not log_group_exists:
        raise LogGroupNotFoundException(log_group_name)


def get_image_build_project(codebuild_client, application, codebase):
    project_name = f"{application}-{codebase}-codebase-image-build"
    response = codebuild_client.batch_get_projects(names=[project_name])

    if bool(response.get("projects")):
        return project_name
    else:
        return f"{application}-{codebase}-codebase-pipeline-image-build"


def get_manual_release_pipeline(codepipeline_client, application, codebase):
    pipeline_name = f"{application}-{codebase}-manual-release"
    try:
        codepipeline_client.get_pipeline(name=pipeline_name)
        return pipeline_name
    except ClientError as e:
        if e.response["Error"]["Code"] == "PipelineNotFoundException":
            return f"{pipeline_name}-pipeline"
