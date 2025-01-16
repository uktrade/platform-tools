import itertools
import random
import re
import string
from pathlib import Path
from typing import Callable
from typing import List
from typing import Union

import boto3
import click

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.load_balancers import ListenerNotFoundException
from dbt_platform_helper.providers.load_balancers import ListenerRuleNotFoundException
from dbt_platform_helper.providers.load_balancers import LoadBalancerNotFoundException
from dbt_platform_helper.providers.load_balancers import find_https_listener
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import Environment
from dbt_platform_helper.utils.application import Service


class MaintenancePageException(PlatformException):
    pass


class LoadBalancedWebServiceNotFoundException(MaintenancePageException):
    pass

    # def __init__(self):
    #     super().__init__("""ECS exec agent never reached "RUNNING" status""")


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


def get_env_ips(vpc: str, application_environment: Environment) -> List[str]:
    account_name = f"{application_environment.session.profile_name}-vpc"
    vpc_name = vpc if vpc else account_name
    ssm_client = application_environment.session.client("ssm")

    try:
        param_value = ssm_client.get_parameter(Name=f"/{vpc_name}/EGRESS_IPS")["Parameter"]["Value"]
    except ssm_client.exceptions.ParameterNotFound:
        click.secho(f"No parameter found with name: /{vpc_name}/EGRESS_IPS")
        raise click.Abort

    return [ip.strip() for ip in param_value.split(",")]


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

    rule_priority = itertools.count(start=1)

    for svc in services:
        target_group_arn = find_target_group(app, env, svc.name, session)

        # not all of an application's services are guaranteed to have been deployed to an environment
        if not target_group_arn:
            continue

        for ip in allowed_ips:
            create_header_rule(
                lb_client,
                listener_arn,
                target_group_arn,
                "X-Forwarded-For",
                [ip],
                "AllowedIps",
                next(rule_priority),
            )
            create_source_ip_rule(
                lb_client,
                listener_arn,
                target_group_arn,
                [ip],
                "AllowedSourceIps",
                next(rule_priority),
            )

        create_header_rule(
            lb_client,
            listener_arn,
            target_group_arn,
            "Bypass-Key",
            [bypass_value],
            "BypassIpFilter",
            next(rule_priority),
        )

        click.secho(
            f"\nUse a browser plugin to add `Bypass-Key` header with value {bypass_value} to your requests. For more detail, visit https://platform.readme.trade.gov.uk/next-steps/put-a-service-under-maintenance/",
            fg="green",
        )

    lb_client.create_rule(
        ListenerArn=listener_arn,
        Priority=next(rule_priority),
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


def remove_maintenance_page(session: boto3.Session, listener_arn: str):
    lb_client = session.client("elbv2")

    rules = lb_client.describe_rules(ListenerArn=listener_arn)["Rules"]
    tag_descriptions = lb_client.describe_tags(ResourceArns=[r["RuleArn"] for r in rules])[
        "TagDescriptions"
    ]

    for name in ["MaintenancePage", "AllowedIps", "BypassIpFilter", "AllowedSourceIps"]:
        deleted = delete_listener_rule(tag_descriptions, name, lb_client)

        if name == "MaintenancePage" and not deleted:
            raise ListenerRuleNotFoundException()


class MaintenancePage:
    def __init__(
        self,
        application: Application,
        user_prompt_callback: Callable[[str], bool] = click.confirm,
        echo: Callable[[str], str] = click.secho,
        find_https_listener: Callable[[boto3.Session, str, str], str] = find_https_listener,
        get_maintenance_page: Callable[
            [boto3.Session, str], Union[str, None]
        ] = get_maintenance_page,
        get_env_ips: Callable[[str, Environment], List[str]] = get_env_ips,
        add_maintenance_page: Callable[
            [boto3.Session, str, str, str, List[Service], tuple, str], None
        ] = add_maintenance_page,
        remove_maintenance_page: Callable[[boto3.Session, str], None] = remove_maintenance_page,
    ):
        self.application = application
        self.user_prompt_callback = user_prompt_callback
        self.echo = echo
        self.find_https_listener = find_https_listener
        self.get_maintenance_page = get_maintenance_page
        self.get_env_ips = get_env_ips
        self.add_maintenance_page = add_maintenance_page
        self.remove_maintenance_page = remove_maintenance_page

    def _get_deployed_load_balanced_web_services(self, app: Application, svc: List[str]):
        if "*" in svc:
            services = [s for s in app.services.values() if s.kind == "Load Balanced Web Service"]
        else:
            all_services = [get_app_service(app, s) for s in list(svc)]
            services = [s for s in all_services if s.kind == "Load Balanced Web Service"]
        if not services:
            raise LoadBalancedWebServiceNotFoundException
        return services

    def activate(self, env: str, services: List[str], template: str, vpc: Union[str, None]):
        try:
            services = self._get_deployed_load_balanced_web_services(self.application, services)
        except LoadBalancedWebServiceNotFoundException:
            # TODO DBTP-1643 - this bit of logic does not depend on env, so env shouldn't really be in the exception
            # message
            # Exception should be propagated to command and caught there.
            self.echo(
                f"No services deployed yet to {self.application.name} environment {env}", fg="red"
            )
            raise click.Abort

        application_environment = get_app_environment(self.application, env)
        try:
            https_listener = self.find_https_listener(
                application_environment.session, self.application.name, env
            )
            current_maintenance_page = self.get_maintenance_page(
                application_environment.session, https_listener
            )
            remove_current_maintenance_page = False
            if current_maintenance_page:
                remove_current_maintenance_page = self.user_prompt_callback(
                    f"There is currently a '{current_maintenance_page}' maintenance page for the {env} "
                    f"environment in {self.application.name}.\nWould you like to replace it with a '{template}' "
                    f"maintenance page?"
                )
                if not remove_current_maintenance_page:
                    raise click.Abort

            if remove_current_maintenance_page or self.user_prompt_callback(
                f"You are about to enable the '{template}' maintenance page for the {env} "
                f"environment in {self.application.name}.\nWould you like to continue?"
            ):
                if current_maintenance_page and remove_current_maintenance_page:
                    self.remove_maintenance_page(application_environment.session, https_listener)

                allowed_ips = self.get_env_ips(vpc, application_environment)

                self.add_maintenance_page(
                    application_environment.session,
                    https_listener,
                    self.application.name,
                    env,
                    services,
                    allowed_ips,
                    template,
                )
                self.echo(
                    f"Maintenance page '{template}' added for environment {env} in application {self.application.name}",
                    fg="green",
                )
            else:
                raise click.Abort

        except LoadBalancerNotFoundException:
            self.echo(
                f"No load balancer found for environment {env} in the application {self.application.name}.",
                fg="red",
            )
            raise click.Abort

        except ListenerNotFoundException:
            self.echo(
                f"No HTTPS listener found for environment {env} in the application {self.application.name}.",
                fg="red",
            )
            raise click.Abort

    def deactivate(self, app, env: str):
        application_environment = get_app_environment(self.application, env)

        try:
            https_listener = find_https_listener(
                application_environment.session, self.application.name, env
            )
            current_maintenance_page = get_maintenance_page(
                application_environment.session, https_listener
            )
            if not current_maintenance_page:
                self.echo("There is no current maintenance page to remove", fg="red")
                raise click.Abort

            if not self.user_prompt_callback(
                f"There is currently a '{current_maintenance_page}' maintenance page, "
                f"would you like to remove it?"
            ):
                raise click.Abort

            remove_maintenance_page(application_environment.session, https_listener)
            self.echo(
                f"Maintenance page removed from environment {env} in application {self.application.name}",
                fg="green",
            )

        except LoadBalancerNotFoundException:
            self.echo(
                f"No load balancer found for environment {env} in the application {self.application.name}.",
                fg="red",
            )
            raise click.Abort

        except ListenerNotFoundException:
            self.echo(
                f"No HTTPS listener found for environment {env} in the application {self.application.name}.",
                fg="red",
            )
            raise click.Abort


def get_app_service(application: Application, svc_name: str) -> Service:
    application_service = application.services.get(svc_name)

    if not application_service:
        click.secho(
            f"The service {svc_name} was not found in the application {application.name}. "
            f"It either does not exist, or has not been deployed.",
            fg="red",
        )
        raise click.Abort

    return application_service


def get_app_environment(application: Application, env_name: str) -> Environment:
    application_environment = application.environments.get(env_name)

    if not application_environment:
        click.secho(
            f"The environment {env_name} was not found in the application {application.name}. "
            f"It either does not exist, or has not been deployed.",
            fg="red",
        )
        raise click.Abort

    return application_environment


def get_rules_tag_descriptions(rules: list, lb_client):
    tag_descriptions = []
    chunk_size = 20

    for i in range(0, len(rules), chunk_size):
        chunk = rules[i : i + chunk_size]
        resource_arns = [r["RuleArn"] for r in chunk]
        response = lb_client.describe_tags(ResourceArns=resource_arns)
        tag_descriptions.extend(response["TagDescriptions"])

    return tag_descriptions


def delete_listener_rule(tag_descriptions: list, tag_name: str, lb_client: boto3.client):
    current_rule_arn = None

    for description in tag_descriptions:
        tags = {t["Key"]: t["Value"] for t in description["Tags"]}
        if tags.get("name") == tag_name:
            current_rule_arn = description["ResourceArn"]
            if current_rule_arn:
                lb_client.delete_rule(RuleArn=current_rule_arn)

    return current_rule_arn


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


def create_header_rule(
    lb_client: boto3.client,
    listener_arn: str,
    target_group_arn: str,
    header_name: str,
    values: list,
    rule_name: str,
    priority: int,
):
    conditions = get_host_conditions(lb_client, listener_arn, target_group_arn)

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


def normalise_to_cidr(ip: str):
    if "/" in ip:
        return ip
    SINGLE_IPV4_CIDR_PREFIX_LENGTH = "32"
    return f"{ip}/{SINGLE_IPV4_CIDR_PREFIX_LENGTH}"


def create_source_ip_rule(
    lb_client: boto3.client,
    listener_arn: str,
    target_group_arn: str,
    values: list,
    rule_name: str,
    priority: int,
):
    conditions = get_host_conditions(lb_client, listener_arn, target_group_arn)

    # add new condition to existing conditions

    combined_conditions = [
        {
            "Field": "source-ip",
            "SourceIpConfig": {"Values": [normalise_to_cidr(value) for value in values]},
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
        f"Creating listener rule {rule_name} for HTTPS Listener with arn {listener_arn}.\n\nIf request source ip matches one of the values {values}, the request will be forwarded to target group with arn {target_group_arn}.",
        fg="green",
    )


def get_host_conditions(lb_client: boto3.client, listener_arn: str, target_group_arn: str):
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

    return conditions
