import re
from pathlib import Path
from typing import Union

import boto3
import click
import requests

from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.files import ensure_cwd_is_repo_root
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.template import setup_templates
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)

AVAILABLE_TEMPLATES = ["default", "migration"]


@click.group(cls=ClickDocOptGroup)
def environment():
    """Commands affecting environments."""
    check_platform_helper_version_needs_update()


@environment.command()
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
@click.option("--svc", type=str, required=True, default="web")
@click.option(
    "--template",
    type=click.Choice(AVAILABLE_TEMPLATES),
    default="default",
    help="The maintenance page you wish to put up.",
)
@click.option("--allowed-ip", "-ip", type=str, multiple=True)
def offline(app, env, svc, template, allowed_ip):
    """Take load-balanced web services offline with a maintenance page."""
    application = load_application(app)
    application_environment = application.environments.get(env)

    if not application_environment:
        click.secho(
            f"The environment {env} was not found in the application {app}. "
            f"It either does not exist, or has not been deployed.",
            fg="red",
        )
        raise click.Abort

    try:
        https_listener = find_https_listener(application_environment.session, app, env)
        current_maintenance_page = get_maintenance_page(
            application_environment.session, https_listener
        )
        remove_current_maintenance_page = False
        if current_maintenance_page:
            remove_current_maintenance_page = click.confirm(
                f"There is currently a '{current_maintenance_page}' maintenance page for the {env} "
                f"environment in {app}.\nWould you like to replace it with a '{template}' "
                f"maintenance page?"
            )
            if not remove_current_maintenance_page:
                raise click.Abort

        if remove_current_maintenance_page or click.confirm(
            f"You are about to enable the '{template}' maintenance page for the {env} "
            f"environment in {app}.\nWould you like to continue?"
        ):
            if current_maintenance_page and remove_current_maintenance_page:
                remove_maintenance_page(application_environment.session, https_listener)

            allowed_ips = list(allowed_ip)
            add_maintenance_page(
                application_environment.session,
                https_listener,
                app,
                env,
                svc,
                allowed_ips,
                template,
            )
            click.secho(
                f"Maintenance page '{template}' added for environment {env} in application {app}",
                fg="green",
            )
        else:
            raise click.Abort

    except LoadBalancerNotFoundError:
        click.secho(
            f"No load balancer found for environment {env} in the application {app}.", fg="red"
        )
        raise click.Abort

    except ListenerNotFoundError:
        click.secho(
            f"No HTTPS listener found for environment {env} in the application {app}.", fg="red"
        )
        raise click.Abort


@environment.command()
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
def online(app, env):
    """Remove a maintenance page from an environment."""
    application = load_application(app)
    application_environment = application.environments.get(env)

    if not application_environment:
        click.secho(
            f"The environment {env} was not found in the application {app}. "
            f"It either does not exist, or has not been deployed.",
            fg="red",
        )
        raise click.Abort

    try:
        https_listener = find_https_listener(application_environment.session, app, env)
        current_maintenance_page = get_maintenance_page(
            application_environment.session, https_listener
        )
        if not current_maintenance_page:
            click.secho("There is no current maintenance page to remove", fg="red")
            raise click.Abort

        if not click.confirm(
            f"There is currently a '{current_maintenance_page}' maintenance page, "
            f"would you like to remove it?"
        ):
            raise click.Abort

        remove_maintenance_page(application_environment.session, https_listener)
        click.secho(
            f"Maintenance page removed from environment {env} in application {app}", fg="green"
        )

    except LoadBalancerNotFoundError:
        click.secho(
            f"No load balancer found for environment {env} in the application {app}.", fg="red"
        )
        raise click.Abort

    except ListenerNotFoundError:
        click.secho(
            f"No HTTPS listener found for environment {env} in the application {app}.", fg="red"
        )
        raise click.Abort


def get_vpc_id(session, env_name, vpc_name=None):
    if not vpc_name:
        vpc_name = f"{session.profile_name}-{env_name}"

    filters = [{"Name": "tag:Name", "Values": [vpc_name]}]
    vpcs = session.client("ec2").describe_vpcs(Filters=filters)["Vpcs"]

    if not vpcs:
        filters[0]["Values"] = [session.profile_name]
        vpcs = session.client("ec2").describe_vpcs(Filters=filters)["Vpcs"]

    if not vpcs:
        click.secho(
            f"No VPC found with name {vpc_name} in AWS account {session.profile_name}.", fg="red"
        )
        raise click.Abort

    return vpcs[0]["VpcId"]


def get_subnet_ids(session, vpc_id):
    subnets = session.client("ec2").describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["Subnets"]

    if not subnets:
        click.secho(f"No subnets found for VPC with id: {vpc_id}.", fg="red")
        raise click.Abort

    public_tag = {"Key": "subnet_type", "Value": "public"}
    public = [subnet["SubnetId"] for subnet in subnets if public_tag in subnet["Tags"]]
    private_tag = {"Key": "subnet_type", "Value": "private"}
    private = [subnet["SubnetId"] for subnet in subnets if private_tag in subnet["Tags"]]

    return public, private


def get_cert_arn(session, env_name):
    certs = session.client("acm").list_certificates()["CertificateSummaryList"]

    for cert in certs:
        if env_name in cert["DomainName"]:
            return cert["CertificateArn"]

    click.secho(f"No certificate found with domain name matching environment {env_name}.", fg="red")
    raise click.Abort


@environment.command()
@click.option("--vpc-name")
@click.option("--name", "-n", multiple=True, required=True)
def generate(name, vpc_name):
    ensure_cwd_is_repo_root()
    session = get_aws_session_or_abort()
    env_template = setup_templates().get_template("env/manifest.yml")

    for env_name in name:
        vpc_id = get_vpc_id(session, env_name, vpc_name)
        pub_subnet_ids, priv_subnet_ids = get_subnet_ids(session, vpc_id)
        cert_arn = get_cert_arn(session, env_name)
        contents = env_template.render(
            {
                "name": env_name,
                "vpc_id": vpc_id,
                "pub_subnet_ids": pub_subnet_ids,
                "priv_subnet_ids": priv_subnet_ids,
                "certificate_arn": cert_arn,
            }
        )

        click.echo(
            mkfile(".", f"copilot/environments/{env_name}/manifest.yml", contents, overwrite=True)
        )


def find_load_balancer(session: boto3.Session, app: str, env: str) -> str:
    lb_client = session.client("elbv2")

    describe_response = lb_client.describe_load_balancers()
    load_balancers = [lb["LoadBalancerArn"] for lb in describe_response["LoadBalancers"]]

    load_balancers = lb_client.describe_tags(ResourceArns=load_balancers)["TagDescriptions"]

    load_balancer_arn = None
    for lb in load_balancers:
        tags = {t["Key"]: t["Value"] for t in lb["Tags"]}
        if tags.get("copilot-application") == app and tags.get("copilot-environment") == env:
            load_balancer_arn = lb["ResourceArn"]

    if not load_balancer_arn:
        raise LoadBalancerNotFoundError()

    return load_balancer_arn


def find_https_listener(session: boto3.Session, app: str, env: str) -> str:
    load_balancer_arn = find_load_balancer(session, app, env)
    lb_client = session.client("elbv2")
    listeners = lb_client.describe_listeners(LoadBalancerArn=load_balancer_arn)["Listeners"]

    listener_arn = None

    try:
        listener_arn = next(l["ListenerArn"] for l in listeners if l["Protocol"] == "HTTPS")
    except StopIteration:
        pass

    if not listener_arn:
        raise ListenerNotFoundError()

    return listener_arn


def find_target_group(app: str, env: str, svc: str) -> str:
    # response = lb_client.describe_target_groups(LoadBalancerArn=load_balancer_arn)
    rg_tagging_client = boto3.client("resourcegroupstaggingapi")
    response = rg_tagging_client.get_resources(
        TagFilters=[
            {
                "Key": "copilot-application",
                "Values": [
                    app,
                ],
                "Key": "copilot-environment",
                "Values": [
                    env,
                ],
                "Key": "copilot-service",
                "Values": [
                    svc,
                ],
            },
        ],
        ResourceTypeFilters=[
            "elasticloadbalancing:targetgroup",
        ],
    )
    for resource in response["ResourceTagMappingList"]:
        tags = {tag["Key"]: tag["Value"] for tag in resource["Tags"]}

        if (
            "copilot-service" in tags
            and tags["copilot-service"] == svc
            and "copilot-environment" in tags
            and tags["copilot-environment"] == env
            and "copilot-application" in tags
            and tags["copilot-application"] == app
        ):
            return resource["ResourceARN"]

    click.secho(
        f"No target group found for application: {app}, environment: {env}, service: {svc}",
        fg="red",
    )
    raise click.Abort


def get_maintenance_page(session: boto3.Session, listener_arn: str) -> Union[str, None]:
    lb_client = session.client("elbv2")

    rules = lb_client.describe_rules(ListenerArn=listener_arn)["Rules"]
    rules = lb_client.describe_tags(ResourceArns=[r["RuleArn"] for r in rules])["TagDescriptions"]

    maintenance_page_type = None
    for rule in rules:
        tags = {t["Key"]: t["Value"] for t in rule["Tags"]}
        if tags.get("name") == "MaintenancePage":
            maintenance_page_type = tags.get("type")

    return maintenance_page_type


def delete_listener_rule(rules: dict, tag_name: str, lb_client):
    for rule in rules:
        tags = {t["Key"]: t["Value"] for t in rule["Tags"]}
        if tags.get("name") == tag_name:
            current_rule_arn = rule["ResourceArn"]

    if not current_rule_arn:
        raise ListenerRuleNotFoundError()

    lb_client.delete_rule(RuleArn=current_rule_arn)


def remove_maintenance_page(session: boto3.Session, listener_arn: str):
    lb_client = session.client("elbv2")

    rules = lb_client.describe_rules(ListenerArn=listener_arn)["Rules"]
    rules = lb_client.describe_tags(ResourceArns=[r["RuleArn"] for r in rules])["TagDescriptions"]

    for name in ["MaintenancePage", "AllowedIps"]:
        delete_listener_rule(rules, name, lb_client)


def get_public_ip():
    response = requests.get("https://api.ipify.org")
    return response.text


def create_allowed_ips_rule(lb_client, listener_arn, allowed_ips, target_group_arn):
    lb_client.create_rule(
        ListenerArn=listener_arn,
        Priority=1,
        Conditions=[
            {
                "Field": "http-header",
                "HttpHeaderConfig": {"HttpHeaderName": "X-Forwarded-For", "Values": allowed_ips},
            }
        ],
        Actions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
        Tags=[
            {"Key": "name", "Value": "AllowedIps"},
        ],
    )


def add_maintenance_page(
    session: boto3.Session,
    listener_arn: str,
    app: str,
    env: str,
    svc: str,
    allowed_ips: tuple,
    template: str = "default",
):
    lb_client = session.client("elbv2")
    maintenance_page_content = get_maintenance_page_template(template)
    user_ip = get_public_ip()
    target_group_arn = find_target_group(app, env, svc)
    allowed_ips = list(allowed_ips) + [user_ip]

    create_allowed_ips_rule(lb_client, listener_arn, allowed_ips, target_group_arn)

    lb_client.create_rule(
        ListenerArn=listener_arn,
        Priority=2,
        Conditions=[
            {
                "Field": "path-pattern",
                "PathPatternConfig": {"Values": ["/*"]},
            }
        ],
        Actions=[
            {
                "Type": "fixed-response",
                "FixedResponseConfig": {
                    "StatusCode": "503",
                    "ContentType": "text/html",
                    "MessageBody": maintenance_page_content,
                },
            }
        ],
        Tags=[
            {"Key": "name", "Value": "MaintenancePage"},
            {"Key": "type", "Value": template},
        ],
    )


def get_maintenance_page_template(template) -> str:
    template_contents = (
        Path(__file__)
        .parent.parent.joinpath(
            f"templates/svc/maintenance_pages/{template}.html",
        )
        .read_text()
        .replace("\n", "")
    )

    # [^\S]\s+ - Remove any space that is not preceded by a non-space character.
    return re.sub(r"[^\S]\s+", "", template_contents)


class LoadBalancerNotFoundError(Exception):
    pass


class ListenerNotFoundError(Exception):
    pass


class ListenerRuleNotFoundError(Exception):
    pass
