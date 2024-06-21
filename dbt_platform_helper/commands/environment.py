import random
import re
import string
from pathlib import Path
from typing import List
from typing import Union

import boto3
import click
import requests
import yaml
from schema import SchemaError

from dbt_platform_helper.utils.application import Environment
from dbt_platform_helper.utils.application import Service
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.files import PLATFORM_CONFIG_FILE
from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.files import config_file_check
from dbt_platform_helper.utils.files import is_terraform_project
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.template import setup_templates
from dbt_platform_helper.utils.validation import PLATFORM_CONFIG_SCHEMA
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)

AVAILABLE_TEMPLATES = ["default", "migration", "dmas-migration"]


@click.group(cls=ClickDocOptGroup)
def environment():
    """Commands affecting environments."""
    check_platform_helper_version_needs_update()


@environment.command()
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
@click.option("--svc", type=str, required=True, multiple=True, default=["web"])
@click.option(
    "--template",
    type=click.Choice(AVAILABLE_TEMPLATES),
    default="default",
    help="The maintenance page you wish to put up.",
)
@click.option("--allowed-ip", "-ip", type=str, multiple=True)
@click.option("--ip-filter", is_flag=True)
def offline(app, env, svc, template, allowed_ip, ip_filter):
    """Take load-balanced web services offline with a maintenance page."""
    application = get_application(app)
    application_environment = get_app_environment(app, env)

    if "*" in svc:
        services = [
            s for s in application.services.values() if s.kind == "Load Balanced Web Service"
        ]
    else:
        all_services = [get_app_service(app, s) for s in list(svc)]
        services = [s for s in all_services if s.kind == "Load Balanced Web Service"]

    if not services:
        click.secho(f"No services deployed yet to {app} environment {env}", fg="red")
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
                services,
                allowed_ips,
                ip_filter,
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
@click.option("--svc", type=str, required=True, default="web")
@click.argument("allowed-ips", nargs=-1)
def allow_ips(app, env, svc, allowed_ips):
    """Allow selected ip addresses to bypass a service's maintenance page."""
    application_environment = get_app_environment(app, env)

    try:
        https_listener = find_https_listener(application_environment.session, app, env)
        current_maintenance_page = get_maintenance_page(
            application_environment.session, https_listener
        )
        if not current_maintenance_page:
            click.secho(
                f"There is no maintenance page currently deployed. To create one, run `platform-helper environment offline --app {app} --env {env} --svc {svc}",
                fg="red",
            )
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

    elbv2_client = application_environment.session.client("elbv2")
    allowed_ips = list(allowed_ips)
    listener_rule = get_listener_rule_by_tag(elbv2_client, https_listener, "name", "AllowedIps")
    current_values = []

    if not listener_rule:
        target_group_arn = find_target_group(app, env, svc)

        if not target_group_arn:
            raise click.Abort

        create_header_rule(
            elbv2_client,
            https_listener,
            target_group_arn,
            "X-Forwarded-For",
            allowed_ips,
            "AllowedIps",
        )
    else:
        x_forwarded_condition = [
            condition
            for condition in listener_rule["Conditions"]
            if condition["Field"] == "http-header"
            and condition["HttpHeaderConfig"]["HttpHeaderName"] == "X-Forwarded-For"
        ][0]
        current_values = x_forwarded_condition["HttpHeaderConfig"]["Values"]
        elbv2_client.modify_rule(
            RuleArn=listener_rule["RuleArn"],
            Conditions=[
                {
                    "Field": "http-header",
                    "HttpHeaderConfig": {
                        "HttpHeaderName": "X-Forwarded-For",
                        "Values": current_values + allowed_ips,
                    },
                }
            ],
        )

    click.secho(
        f"The following ips now have access to the {svc} service: {', '.join(current_values + allowed_ips)}",
        fg="green",
    )


@environment.command()
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
def online(app, env):
    """Remove a maintenance page from an environment."""
    application_environment = get_app_environment(app, env)

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


def get_application(app_name: str):
    return load_application(app_name)


def get_app_environment(app_name: str, env_name: str) -> Environment:
    application = get_application(app_name)
    application_environment = application.environments.get(env_name)

    if not application_environment:
        click.secho(
            f"The environment {env_name} was not found in the application {app_name}. "
            f"It either does not exist, or has not been deployed.",
            fg="red",
        )
        raise click.Abort

    return application_environment


def get_app_service(app_name: str, svc_name: str) -> Service:
    application = get_application(app_name)
    application_service = application.services.get(svc_name)

    if not application_service:
        click.secho(
            f"The service {svc_name} was not found in the application {app_name}. "
            f"It either does not exist, or has not been deployed.",
            fg="red",
        )
        raise click.Abort

    return application_service


def get_listener_rule_by_tag(elbv2_client, listener_arn, tag_key, tag_value):
    response = elbv2_client.describe_rules(ListenerArn=listener_arn)
    for rule in response["Rules"]:
        rule_arn = rule["RuleArn"]

        tags_response = elbv2_client.describe_tags(ResourceArns=[rule_arn])
        for tag_description in tags_response["TagDescriptions"]:
            for tag in tag_description["Tags"]:
                if tag["Key"] == tag_key and tag["Value"] == tag_value:
                    return rule


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
@click.option("--vpc-name", hidden=True)
@click.option("--name", "-n", required=True)
def generate(name, vpc_name):
    if vpc_name:
        click.secho(
            f"This option is deprecated. Please add the VPC name for your envs to {PLATFORM_CONFIG_FILE}",
            fg="red",
        )
        raise click.Abort

    config_file_check()
    conf = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())

    try:
        PLATFORM_CONFIG_SCHEMA.validate(conf)
    except SchemaError as ex:
        click.secho(f"Invalid `{PLATFORM_CONFIG_FILE}` file: {str(ex)}", fg="red")
        raise click.Abort

    env_config = apply_environment_defaults(conf)["environments"][name]

    _generate_copilot_environment_manifests(name, env_config)


@environment.command()
@click.option("--name", "-n", required=True)
def generate_terraform(name):
    config_file_check()
    if not is_terraform_project():
        click.secho("This is not a terraform project. Exiting.", fg="red")
        exit(1)

    conf = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())

    try:
        PLATFORM_CONFIG_SCHEMA.validate(conf)
    except SchemaError as ex:
        click.secho(f"Invalid `{PLATFORM_CONFIG_FILE}` file: {str(ex)}", fg="red")
        raise click.Abort

    env_config = apply_environment_defaults(conf)["environments"][name]
    _generate_terraform_environment_manifests(conf["application"], name, env_config)


def _generate_copilot_environment_manifests(name, env_config):
    session = get_aws_session_or_abort()
    env_template = setup_templates().get_template("env/manifest.yml")
    vpc_name = env_config.get("vpc", None)
    vpc_id = get_vpc_id(session, name, vpc_name)
    pub_subnet_ids, priv_subnet_ids = get_subnet_ids(session, vpc_id)
    cert_arn = get_cert_arn(session, name)
    contents = env_template.render(
        {
            "name": name,
            "vpc_id": vpc_id,
            "pub_subnet_ids": pub_subnet_ids,
            "priv_subnet_ids": priv_subnet_ids,
            "certificate_arn": cert_arn,
        }
    )
    click.echo(mkfile(".", f"copilot/environments/{name}/manifest.yml", contents, overwrite=True))


def _generate_terraform_environment_manifests(application, env, env_config):
    env_template = setup_templates().get_template("environments/main.tf")

    contents = env_template.render(
        {"application": application, "environment": env, "config": env_config}
    )

    click.echo(mkfile(".", f"terraform/environments/{env}/main.tf", contents, overwrite=True))


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

    return None


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


def delete_listener_rule(rules: list, tag_name: str, lb_client: boto3.client):
    current_rule_arn = None

    for rule in rules:
        tags = {t["Key"]: t["Value"] for t in rule["Tags"]}
        if tags.get("name") == tag_name:
            current_rule_arn = rule["ResourceArn"]

    if not current_rule_arn:
        return current_rule_arn

    lb_client.delete_rule(RuleArn=current_rule_arn)

    return current_rule_arn


def remove_maintenance_page(session: boto3.Session, listener_arn: str):
    lb_client = session.client("elbv2")

    rules = lb_client.describe_rules(ListenerArn=listener_arn)["Rules"]
    rules = lb_client.describe_tags(ResourceArns=[r["RuleArn"] for r in rules])["TagDescriptions"]

    for name in ["MaintenancePage", "AllowedIps", "BypassIpFilter"]:
        deleted = delete_listener_rule(rules, name, lb_client)

        if name == "MaintenancePage" and not deleted:
            raise ListenerRuleNotFoundError()


def get_public_ip():
    response = requests.get("https://api.ipify.org")
    return response.text


def create_header_rule(
    lb_client: boto3.client,
    listener_arn: str,
    target_group_arn: str,
    header_name: str,
    values: list,
    rule_name: str,
):
    lb_client.create_rule(
        ListenerArn=listener_arn,
        Priority=1,
        Conditions=[
            {
                "Field": "http-header",
                "HttpHeaderConfig": {"HttpHeaderName": header_name, "Values": values},
            }
        ],
        Actions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
        Tags=[
            {"Key": "name", "Value": rule_name},
        ],
    )

    click.secho(
        f"Creating listener rule {rule_name} for HTTPS Listener with arn {listener_arn}.\n\nIf request header {header_name} contains one of the values {values}, the request will be forwarded to target group with arn {target_group_arn}.",
        fg="green",
    )


def add_maintenance_page(
    session: boto3.Session,
    listener_arn: str,
    app: str,
    env: str,
    services: List[Service],
    allowed_ips: tuple,
    ip_filter: bool,
    template: str = "default",
):
    lb_client = session.client("elbv2")
    maintenance_page_content = get_maintenance_page_template(template)

    for svc in services:
        target_group_arn = find_target_group(app, env, svc.name)

        # not all of an application's services are guaranteed to have been deployed to an environment
        if not target_group_arn:
            continue

        if not ip_filter:
            user_ip = get_public_ip()
            allowed_ips = list(allowed_ips) + [user_ip]

            create_header_rule(
                lb_client,
                listener_arn,
                target_group_arn,
                "X-Forwarded-For",
                allowed_ips,
                "AllowedIps",
            )
        else:
            bypass_value = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
            create_header_rule(
                lb_client,
                listener_arn,
                target_group_arn,
                "Bypass-Key",
                [bypass_value],
                "BypassIpFilter",
            )

            click.secho(
                f"\nUse a browser plugin to add `Bypass-Key` header with value {bypass_value} to your requests. For more detail, visit https://platform.readme.trade.gov.uk/ ",
                fg="green",
            )

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
