import random
import re
import string
from pathlib import Path
from typing import List
from typing import Union

import boto3
import click
from schema import SchemaError

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.utils.application import Environment
from dbt_platform_helper.utils.application import Service
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.platform_config import is_terraform_project
from dbt_platform_helper.utils.template import setup_templates
from dbt_platform_helper.utils.validation import load_and_validate_platform_config
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
@click.option("--vpc", type=str)
def offline(app, env, svc, template, vpc):
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

            allowed_ips = get_env_ips(vpc, application_environment)

            add_maintenance_page(
                application_environment.session,
                https_listener,
                app,
                env,
                services,
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


def get_env_ips(vpc: str, application_environment: Environment):
    account_name = f"{application_environment.session.profile_name}-vpc"
    vpc_name = vpc if vpc else account_name
    ssm_client = application_environment.session.client("ssm")

    try:
        param_value = ssm_client.get_parameter(Name=f"/{vpc_name}/EGRESS_IPS")["Parameter"]["Value"]
    except ssm_client.exceptions.ParameterNotFound:
        click.secho(f"No parameter found with name: /{vpc_name}/EGRESS_IPS")
        raise click.Abort

    return [ip.strip() for ip in param_value.split(",")]


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

    session = get_aws_session_or_abort()

    try:
        conf = load_and_validate_platform_config()
    except SchemaError as ex:
        click.secho(f"Invalid `{PLATFORM_CONFIG_FILE}` file: {str(ex)}", fg="red")
        raise click.Abort

    env_config = apply_environment_defaults(conf)["environments"][name]

    _generate_copilot_environment_manifests(name, env_config, session)


@environment.command(help="Generate terraform manifest for the specified environment.")
@click.option(
    "--name", "-n", required=True, help="The name of the environment to generate a manifest for."
)
@click.option(
    "--terraform-platform-modules-version",
    help=f"Override the default version of terraform-platform-modules. (Default version is '{DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION}').",
)
def generate_terraform(name, terraform_platform_modules_version):
    if not is_terraform_project():
        click.secho("This is not a terraform project. Exiting.", fg="red")
        exit(1)

    conf = load_and_validate_platform_config()

    env_config = apply_environment_defaults(conf)["environments"][name]
    _generate_terraform_environment_manifests(
        conf["application"], name, env_config, terraform_platform_modules_version
    )


def _generate_copilot_environment_manifests(name, env_config, session):
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


def _generate_terraform_environment_manifests(
    application, env, env_config, cli_terraform_platform_modules_version
):
    env_template = setup_templates().get_template("environments/main.tf")

    terraform_platform_modules_version = _determine_terraform_platform_modules_version(
        env_config, cli_terraform_platform_modules_version
    )

    contents = env_template.render(
        {
            "application": application,
            "environment": env,
            "config": env_config,
            "terraform_platform_modules_version": terraform_platform_modules_version,
        }
    )

    click.echo(mkfile(".", f"terraform/environments/{env}/main.tf", contents, overwrite=True))


def _determine_terraform_platform_modules_version(env_conf, cli_terraform_platform_modules_version):
    cli_terraform_platform_modules_version = cli_terraform_platform_modules_version
    env_conf_terraform_platform_modules_version = env_conf.get("versions", {}).get(
        "terraform-platform-modules"
    )
    version_preference_order = [
        cli_terraform_platform_modules_version,
        env_conf_terraform_platform_modules_version,
        DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION,
    ]
    return [version for version in version_preference_order if version][0]


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


def find_target_group(app: str, env: str, svc: str, session: boto3.Session) -> str:
    rg_tagging_client = session.client("resourcegroupstaggingapi")
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
    tag_descriptions = get_rules_tag_descriptions(rules, lb_client)

    maintenance_page_type = None
    for description in tag_descriptions:
        tags = {t["Key"]: t["Value"] for t in description["Tags"]}
        if tags.get("name") == "MaintenancePage":
            maintenance_page_type = tags.get("type")

    return maintenance_page_type


def delete_listener_rule(tag_descriptions: list, tag_name: str, lb_client: boto3.client):
    current_rule_arn = None

    for description in tag_descriptions:
        tags = {t["Key"]: t["Value"] for t in description["Tags"]}
        if tags.get("name") == tag_name:
            current_rule_arn = description["ResourceArn"]

    if not current_rule_arn:
        return current_rule_arn

    lb_client.delete_rule(RuleArn=current_rule_arn)

    return current_rule_arn


def remove_maintenance_page(session: boto3.Session, listener_arn: str):
    lb_client = session.client("elbv2")

    rules = lb_client.describe_rules(ListenerArn=listener_arn)["Rules"]
    tag_descriptions = get_rules_tag_descriptions(rules, lb_client)
    tag_descriptions = lb_client.describe_tags(ResourceArns=[r["RuleArn"] for r in rules])[
        "TagDescriptions"
    ]

    for name in ["MaintenancePage", "AllowedIps", "BypassIpFilter"]:
        deleted = delete_listener_rule(tag_descriptions, name, lb_client)

        if name == "MaintenancePage" and not deleted:
            raise ListenerRuleNotFoundError()


def get_rules_tag_descriptions(rules: list, lb_client):
    tag_descriptions = []
    chunk_size = 20

    for i in range(0, len(rules), chunk_size):
        chunk = rules[i : i + chunk_size]
        resource_arns = [r["RuleArn"] for r in chunk]
        response = lb_client.describe_tags(ResourceArns=resource_arns)
        tag_descriptions.extend(response["TagDescriptions"])

    return tag_descriptions


def create_header_rule(
    lb_client: boto3.client,
    listener_arn: str,
    target_group_arn: str,
    header_name: str,
    values: list,
    rule_name: str,
    priority: int,
):
    rules = lb_client.describe_rules(ListenerArn=listener_arn)["Rules"]

    # Get current set of forwarding conditions for the target group
    for rule in rules:
        for action in rule["Actions"]:
            if action["Type"] == "forward" and action["TargetGroupArn"] == target_group_arn:
                conditions = rule["Conditions"]

    # filter to host-header conditions
    conditions = [
        {i: condition[i] for i in condition if i != "Values"}
        for condition in conditions
        if condition["Field"] == "host-header"
    ]

    # remove internal hosts
    conditions[0]["HostHeaderConfig"]["Values"] = [
        v for v in conditions[0]["HostHeaderConfig"]["Values"]
    ]

    # add new condition to existing conditions
    combined_conditions = [
        {
            "Field": "http-header",
            "HttpHeaderConfig": {"HttpHeaderName": header_name, "Values": values},
        }
    ] + conditions

    lb_client.create_rule(
        ListenerArn=listener_arn,
        Priority=priority,
        Conditions=combined_conditions,
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
    template: str = "default",
):
    lb_client = session.client("elbv2")
    maintenance_page_content = get_maintenance_page_template(template)
    bypass_value = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))

    service_number = 1

    for svc in services:
        target_group_arn = find_target_group(app, env, svc.name, session)

        # not all of an application's services are guaranteed to have been deployed to an environment
        if not target_group_arn:
            continue

        allowed_ips = list(allowed_ips)
        max_allowed_ips = 100
        for ip_index, ip in enumerate(allowed_ips):
            forwarded_rule_priority = (service_number * max_allowed_ips) + ip_index
            create_header_rule(
                lb_client,
                listener_arn,
                target_group_arn,
                "X-Forwarded-For",
                [ip],
                "AllowedIps",
                forwarded_rule_priority,
            )

        bypass_rule_priority = service_number
        create_header_rule(
            lb_client,
            listener_arn,
            target_group_arn,
            "Bypass-Key",
            [bypass_value],
            "BypassIpFilter",
            bypass_rule_priority,
        )

        service_number += 1

        click.secho(
            f"\nUse a browser plugin to add `Bypass-Key` header with value {bypass_value} to your requests. For more detail, visit https://platform.readme.trade.gov.uk/activities/holding-and-maintenance-pages/",
            fg="green",
        )

    fixed_rule_priority = (service_number + 5) * max_allowed_ips
    lb_client.create_rule(
        ListenerArn=listener_arn,
        Priority=fixed_rule_priority,  # big number because we create multiple higher priority "AllowedIps" rules for each allowed ip for each service above.
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
