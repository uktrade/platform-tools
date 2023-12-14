import re
from pathlib import Path
from typing import Union

import boto3
import click

from dbt_copilot_helper.utils.application import load_application
from dbt_copilot_helper.utils.click import ClickDocOptGroup
from dbt_copilot_helper.utils.versioning import (
    check_copilot_helper_version_needs_update,
)

AVAILABLE_TEMPLATES = ["default", "migration"]


@click.group(cls=ClickDocOptGroup)
def environment():
    """Commands affecting environments."""
    check_copilot_helper_version_needs_update()


@environment.command()
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
@click.option(
    "--template",
    type=click.Choice(AVAILABLE_TEMPLATES),
    default="default",
    help="The maintenance page you wish to put up.",
)
def offline(app, env, template):
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

            add_maintenance_page(application_environment.session, https_listener, template)
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


def remove_maintenance_page(session: boto3.Session, listener_arn: str):
    lb_client = session.client("elbv2")

    rules = lb_client.describe_rules(ListenerArn=listener_arn)["Rules"]
    rules = lb_client.describe_tags(ResourceArns=[r["RuleArn"] for r in rules])["TagDescriptions"]

    current_rule_arn = None
    for rule in rules:
        tags = {t["Key"]: t["Value"] for t in rule["Tags"]}
        if tags.get("name") == "MaintenancePage":
            current_rule_arn = rule["ResourceArn"]

    if not current_rule_arn:
        raise ListenerRuleNotFoundError()

    lb_client.delete_rule(RuleArn=current_rule_arn)


def add_maintenance_page(session: boto3.Session, listener_arn: str, template: str = "default"):
    lb_client = session.client("elbv2")
    maintenance_page_content = get_maintenance_page_template(template)

    lb_client.create_rule(
        ListenerArn=listener_arn,
        Priority=1,
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
