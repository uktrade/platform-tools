import os
from configparser import ConfigParser
from pathlib import Path
from typing import Tuple

import boto3
import botocore
import click
import yaml
from boto3 import Session

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
    except botocore.exceptions.TokenRetrievalError:
        click.secho(
            "The SSO Token associated with this profile has expired.  "
            "To refresh this SSO session run `aws sso login` with the corresponding profile",
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


def get_ssm_secrets(app, env):
    """Return secrets from AWS Parameter Store as a list of tuples with the
    secret name and secret value."""

    session = get_aws_session_or_abort()
    client = session.client("ssm")

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


def check_response(response):
    if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
        click.secho(
            f"Unknown response error from AWS.\nStatus Code: {response['ResponseMetadata']['HTTPStatusCode']}",
            fg="red",
        )
        exit()


def get_codestar_connection_arn(app_name):
    session = get_aws_session_or_abort()
    response = session.client("codestar-connections").list_connections()

    for connection in response["Connections"]:
        if connection["ConnectionName"] == app_name:
            return connection["ConnectionArn"]


def get_load_balancer_domain_and_configuration(
    project_session: Session, app: str, svc: str, env: str
) -> Tuple[str, dict]:
    response = get_load_balancer_configuration(project_session, app, svc, env)

    # Find the domain name
    with open(f"./copilot/{svc}/manifest.yml", "r") as fd:
        conf = yaml.safe_load(fd)
        if "environments" in conf:
            if env in conf["environments"]:
                for domain in conf["environments"].items():
                    if domain[0] == env:
                        if (
                            domain[1] is None
                            or domain[1]["http"] is None
                            or domain[1]["http"]["alias"] is None
                        ):
                            click.secho(
                                f"No domains found, please check the ./copilot/{svc}/manifest.yml file",
                                fg="red",
                            )
                            exit()
                        domain_name = domain[1]["http"]["alias"]
            else:
                click.secho(
                    f"Environment {env} not found, please check the ./copilot/{svc}/manifest.yml file",
                    fg="red",
                )
                exit()

    return domain_name, response["LoadBalancers"][0]


def get_load_balancer_configuration(
    project_session: Session, app: str, svc: str, env: str
) -> list[Session]:
    def separate_hyphenated_application_environment_and_service(
        hyphenated_string, number_of_items_of_interest, number_of_trailing_items
    ):
        # The application name may be hyphenated, so we start splitting
        # at the hyphen after the first item of interest and return the
        # items of interest only...
        return hyphenated_string.rsplit(
            "-", number_of_trailing_items + number_of_items_of_interest - 1
        )[:number_of_items_of_interest]

    proj_client = project_session.client("ecs")

    response = proj_client.list_clusters()
    check_response(response)
    no_items = True
    for cluster_arn in response["clusterArns"]:
        cluster_name = cluster_arn.split("/")[1]
        cluster_app, cluster_env = separate_hyphenated_application_environment_and_service(
            cluster_name, 2, 2
        )
        if cluster_app == app and cluster_env == env:
            no_items = False
            break

    if no_items:
        click.echo(
            click.style("There are no clusters matching ", fg="red")
            + click.style(f"{app} ", fg="white", bold=True)
            + click.style("in this AWS account", fg="red"),
        )
        exit()

    response = proj_client.list_services(cluster=cluster_name)
    check_response(response)
    no_items = True
    for service_arn in response["serviceArns"]:
        fully_qualified_service_name = service_arn.split("/")[2]
        (
            service_app,
            service_env,
            service_name,
        ) = separate_hyphenated_application_environment_and_service(
            fully_qualified_service_name, 3, 2
        )
        if service_app == app and service_env == env and service_name == svc:
            no_items = False
            break

    if no_items:
        click.echo(
            click.style("There are no services matching ", fg="red")
            + click.style(f"{svc}", fg="white", bold=True)
            + click.style(" in this aws account", fg="red"),
        )
        exit()

    elb_client = project_session.client("elbv2")

    elb_arn = elb_client.describe_target_groups(
        TargetGroupArns=[
            proj_client.describe_services(
                cluster=cluster_name,
                services=[
                    fully_qualified_service_name,
                ],
            )["services"][0]["loadBalancers"][0]["targetGroupArn"],
        ],
    )["TargetGroups"][0]["LoadBalancerArns"][0]

    response = elb_client.describe_load_balancers(LoadBalancerArns=[elb_arn])
    check_response(response)
    return response
