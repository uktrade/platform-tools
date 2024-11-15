import json
import os
import urllib.parse
from configparser import ConfigParser
from pathlib import Path
from typing import Tuple

import boto3
import botocore
import botocore.exceptions
import click
import yaml
from boto3 import Session

from dbt_platform_helper.exceptions import AWSException
from dbt_platform_helper.exceptions import CopilotCodebaseNotFoundError
from dbt_platform_helper.exceptions import ImageNotFoundError
from dbt_platform_helper.exceptions import ValidationException
from dbt_platform_helper.utils.files import cache_refresh_required
from dbt_platform_helper.utils.files import read_supported_versions_from_cache
from dbt_platform_helper.utils.files import write_to_cache

SSM_BASE_PATH = "/copilot/{app}/{env}/secrets/"
SSM_PATH = "/copilot/{app}/{env}/secrets/{name}"
AWS_SESSION_CACHE = {}


def get_aws_session_or_abort(aws_profile: str = None) -> boto3.session.Session:
    REFRESH_TOKEN_MESSAGE = (
        "To refresh this SSO session run `aws sso login` with the corresponding profile"
    )
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


class NoProfileForAccountIdError(Exception):
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


def get_account_details(sts_client=None):
    if not sts_client:
        sts_client = get_aws_session_or_abort().client("sts")
    response = sts_client.get_caller_identity()

    return response["Account"], response["UserId"]


def get_public_repository_arn(repository_uri):
    session = get_aws_session_or_abort()
    response = session.client("ecr-public", region_name="us-east-1").describe_repositories()
    repository = [
        repo for repo in response["repositories"] if repo["repositoryUri"] == repository_uri
    ]

    return repository[0]["repositoryArn"] if repository else None


def get_load_balancer_domain_and_configuration(
    project_session: Session, app: str, env: str, svc: str
) -> Tuple[str, dict]:
    response = get_load_balancer_configuration(project_session, app, env, svc)

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
    project_session: Session, app: str, env: str, svc: str
) -> list[Session]:
    proj_client = project_session.client("ecs")

    response = proj_client.list_clusters()
    check_response(response)
    no_items = True
    for cluster_arn in response["clusterArns"]:
        cluster_name = cluster_arn.split("/")[1]
        if cluster_name.startswith(f"{app}-{env}-Cluster"):
            no_items = False
            break

    if no_items:
        click.echo(
            click.style("There are no clusters for environment ", fg="red")
            + click.style(f"{env} ", fg="white", bold=True)
            + click.style("of application ", fg="red")
            + click.style(f"{app} ", fg="white", bold=True)
            + click.style("in AWS account ", fg="red")
            + click.style(f"{project_session.profile_name}", fg="white", bold=True),
        )
        exit()

    response = proj_client.list_services(cluster=cluster_name)
    check_response(response)
    no_items = True
    for service_arn in response["serviceArns"]:
        fully_qualified_service_name = service_arn.split("/")[2]
        if fully_qualified_service_name.startswith(f"{app}-{env}-{svc}-Service"):
            no_items = False
            break

    if no_items:
        click.echo(
            click.style("There are no services called ", fg="red")
            + click.style(f"{svc} ", fg="white", bold=True)
            + click.style("for environment ", fg="red")
            + click.style(f"{env} ", fg="white", bold=True)
            + click.style("of application ", fg="red")
            + click.style(f"{app} ", fg="white", bold=True)
            + click.style("in AWS account ", fg="red")
            + click.style(f"{project_session.profile_name}", fg="white", bold=True),
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


def get_postgres_connection_data_updated_with_master_secret(session, parameter_name, secret_arn):
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


def get_supported_redis_versions():

    if cache_refresh_required("redis"):

        supported_versions = []

        session = get_aws_session_or_abort()
        elasticache_client = session.client("elasticache")

        supported_versions_response = elasticache_client.describe_cache_engine_versions(
            Engine="redis"
        )

        supported_versions = [
            version["EngineVersion"]
            for version in supported_versions_response["CacheEngineVersions"]
        ]

        write_to_cache("redis", supported_versions)

        return supported_versions

    else:
        return read_supported_versions_from_cache("redis")


def get_supported_opensearch_versions():

    if cache_refresh_required("opensearch"):

        supported_versions = []

        session = get_aws_session_or_abort()
        opensearch_client = session.client("opensearch")

        response = opensearch_client.list_versions()
        all_versions = response["Versions"]

        opensearch_versions = [
            version for version in all_versions if not version.startswith("Elasticsearch_")
        ]
        supported_versions = [
            version.removeprefix("OpenSearch_") for version in opensearch_versions
        ]

        write_to_cache("opensearch", supported_versions)

        return supported_versions

    else:
        return read_supported_versions_from_cache("opensearch")


def get_connection_string(
    session: Session,
    app: str,
    env: str,
    db_identifier: str,
    connection_data_fn=get_postgres_connection_data_updated_with_master_secret,
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

    conn = connection_data_fn(session, connection_string_parameter, master_secret_arn)

    return f"postgres://{conn['username']}:{conn['password']}@{conn['host']}:{conn['port']}/{conn['dbname']}"


class Vpc:
    def __init__(self, subnets: list[str], security_groups: list[str]):
        self.subnets = subnets
        self.security_groups = security_groups


def get_vpc_info_by_name(session: Session, app: str, env: str, vpc_name: str) -> Vpc:
    ec2_client = session.client("ec2")
    vpc_response = ec2_client.describe_vpcs(Filters=[{"Name": "tag:Name", "Values": [vpc_name]}])

    matching_vpcs = vpc_response.get("Vpcs", [])

    if not matching_vpcs:
        raise AWSException(f"VPC not found for name '{vpc_name}'")

    vpc_id = vpc_response["Vpcs"][0].get("VpcId")

    if not vpc_id:
        raise AWSException(f"VPC id not present in vpc '{vpc_name}'")

    ec2_resource = session.resource("ec2")
    vpc = ec2_resource.Vpc(vpc_id)

    route_tables = ec2_client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["RouteTables"]

    subnets = []
    for route_table in route_tables:
        private_routes = [route for route in route_table["Routes"] if "NatGatewayId" in route]
        if not private_routes:
            continue
        for association in route_table["Associations"]:
            if "SubnetId" in association:
                subnet_id = association["SubnetId"]
                subnets.append(subnet_id)

    if not subnets:
        raise AWSException(f"No private subnets found in vpc '{vpc_name}'")

    tag_value = {"Key": "Name", "Value": f"copilot-{app}-{env}-env"}
    sec_groups = [sg.id for sg in vpc.security_groups.all() if sg.tags and tag_value in sg.tags]

    if not sec_groups:
        raise AWSException(f"No matching security groups found in vpc '{vpc_name}'")

    return Vpc(subnets, sec_groups)


def start_build_extraction(codebuild_client, build_options):
    response = codebuild_client.start_build(**build_options)
    return response["build"]["arn"]


def check_codebase_exists(session: Session, application, codebase: str):
    try:
        ssm_client = session.client("ssm")
        ssm_client.get_parameter(
            Name=f"/copilot/applications/{application.name}/codebases/{codebase}"
        )["Parameter"]["Value"]
    except (
        KeyError,
        ValueError,
        ssm_client.exceptions.ParameterNotFound,
    ):
        raise CopilotCodebaseNotFoundError


def check_image_exists(session, application, codebase, commit):
    ecr_client = session.client("ecr")
    try:
        ecr_client.describe_images(
            repositoryName=f"{application.name}/{codebase}",
            imageIds=[{"imageTag": f"commit-{commit}"}],
        )
    except (
        ecr_client.exceptions.RepositoryNotFoundException,
        ecr_client.exceptions.ImageNotFoundException,
    ):
        raise ImageNotFoundError


def get_build_url_from_arn(build_arn: str) -> str:
    _, _, _, region, account_id, project_name, build_id = build_arn.split(":")
    project_name = project_name.removeprefix("build/")
    return (
        f"https://eu-west-2.console.aws.amazon.com/codesuite/codebuild/{account_id}/projects/"
        f"{project_name}/build/{project_name}%3A{build_id}"
    )


def list_latest_images(ecr_client, ecr_repository_name, codebase_repository, echo_fn):
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
            echo_fn(
                f"  - https://github.com/{codebase_repository}/commit/{commit_hash} - published: {image['imagePushedAt']}"
            )
        except StopIteration:
            continue
