#!/usr/bin/env python
import time
import uuid
from pathlib import Path

import boto3
import botocore  # noqa
import cfn_flip.yaml_dumper
import click
import yaml
from cfn_tools import load_yaml

from dbt_copilot_helper.commands.dns import get_load_balancer_domain_and_configuration
from dbt_copilot_helper.utils.aws import check_aws_conn
from dbt_copilot_helper.utils.aws import check_response
from dbt_copilot_helper.utils.click import ClickDocOptGroup
from dbt_copilot_helper.utils.cloudformation import get_lint_result
from dbt_copilot_helper.utils.files import ensure_cwd_is_repo_root
from dbt_copilot_helper.utils.versioning import (
    check_copilot_helper_version_needs_update,
)

# This may need to change, once we determine what the default WAF name will be.
WAF_DEFAULT_NAME = "default"


def check_waf(project_session: boto3.Session) -> str:
    click.secho("Checking WAF exists", fg="cyan")
    client = project_session.client("wafv2")

    response = client.list_web_acls(Scope="REGIONAL")
    arn = ""
    for waf in response["WebACLs"]:
        if waf["Name"] == WAF_DEFAULT_NAME:
            arn = waf["ARN"]
    return arn


@click.group(chain=True, cls=ClickDocOptGroup)
def waf():
    check_copilot_helper_version_needs_update()


@waf.command()
@click.option("--app", help="Application Name", required=True)
@click.option("--env", help="Environment", required=True)
@click.option("--svc", help="Service Name", required=True)
@click.option(
    "--project-profile", help="AWS account profile name for application account", required=True
)
def attach_waf(app, project_profile, svc, env):
    """Attach default WAF rule to ECS Load Balancer."""

    project_session = check_aws_conn(project_profile)
    waf_arn = check_waf(project_session)
    if not waf_arn:
        click.secho(
            "Default WAF rule does not exists in this AWS account, "
            "please have this created by the SRE team",
            fg="red",
        )
        exit()

    domain_name, load_balancer_configuration = get_load_balancer_domain_and_configuration(
        project_session, app, svc, env
    )

    elb_arn = load_balancer_configuration["LoadBalancerArn"]
    elb_name = load_balancer_configuration["DNSName"]
    waf_client = project_session.client("wafv2")

    response = waf_client.associate_web_acl(WebACLArn=waf_arn, ResourceArn=elb_arn)
    check_response(response)
    click.echo(
        click.style("Default WAF is now associated with ", fg="green")
        + click.style(f"{elb_name} ", fg="white", bold=True)
        + click.style("for domain ", fg="green")
        + click.style(f"{domain_name}", fg="white", bold=True),
    )


def create_stack(cf_client, app, svc, env, raw):
    return cf_client.create_stack(
        StackName=f"{app}-{svc}-{env}-CustomWAFStack",
        TemplateBody=raw,
        TimeoutInMinutes=5,
        OnFailure="DELETE",
        Tags=[
            {"Key": "Name", "Value": "copilot tools custom waf"},
        ],
        ClientRequestToken=uuid.uuid4().hex,
        EnableTerminationProtection=False,
    )


@waf.command()
@click.option("--app", help="Application Name", required=True)
@click.option("--env", help="Environment", required=True)
@click.option("--svc", help="Service Name", required=True)
@click.option(
    "--project-profile", help="AWS account profile name for application account", required=True
)
@click.option("--waf-path", help="path to waf.yml file", required=True)
def custom_waf(app, project_profile, svc, env, waf_path):
    """Attach custom WAF to ECS Load Balancer."""

    project_session = check_aws_conn(project_profile)
    ensure_cwd_is_repo_root()
    path = Path().resolve() / waf_path

    # The YAML data_dict needs verification, need to create a function to lint/check YAML formatting.
    result = get_lint_result(str(path))
    if result.returncode != 0:
        click.secho(f"File failed lint check.\n{str(path)}", fg="red")
        exit()

    try:
        with open(path, "r") as fd:
            data_dict = load_yaml(fd)
    except FileNotFoundError:
        click.secho(f"File not found...\n{path}", fg="red")
        exit()

    # dumper is used to resolve the shorthand in YAML file, eg !GetAtt
    dumper = cfn_flip.yaml_dumper.get_dumper(clean_up=True, long_form=False)
    raw = yaml.dump(data_dict, Dumper=dumper, default_flow_style=False, allow_unicode=True)

    cf_client = project_session.client("cloudformation")

    try:
        cs_response = create_stack(cf_client, app, svc, env, raw)
    except cf_client.exceptions.AlreadyExistsException:
        click.echo(
            click.style(
                "CloudFormation Stack already exists, please delete the stack first.\n", fg="red"
            )
            + click.style(f"{app}-{svc}-{env}-CustomWAFStack", fg="red"),
        )
        exit()

    check_response(cs_response)

    response = cf_client.describe_stacks(StackName=cs_response["StackId"])
    while response["Stacks"][0]["StackStatus"] == "CREATE_IN_PROGRESS":
        click.secho("Waiting for WAF resource to be created...", fg="yellow")
        time.sleep(2)
        response = cf_client.describe_stacks(StackName=cs_response["StackId"])

    if response["Stacks"][0]["StackStatus"] == "DELETE_IN_PROGRESS":
        click.secho(
            "Failed to create CloudFormation stack, see AWS webconsole for details", fg="red"
        )
        exit()

    waf_arn = response["Stacks"][0]["Outputs"][0]["OutputValue"]
    click.echo(
        click.style("WAF created: ", fg="yellow") + click.style(f"{waf_arn}", fg="white", bold=True)
    )

    domain_name, load_balancer_configuration = get_load_balancer_domain_and_configuration(
        project_session, app, svc, env
    )
    elb_arn = load_balancer_configuration["LoadBalancerArn"]
    elb_name = load_balancer_configuration["DNSName"]
    waf_client = project_session.client("wafv2")

    # It takes a few seconds for the WAF to be available to use.
    while True:
        try:
            response = waf_client.associate_web_acl(WebACLArn=waf_arn, ResourceArn=elb_arn)
        except waf_client.exceptions.WAFUnavailableEntityException:
            click.secho("Waiting for WAF resource to be available...", fg="yellow")
            time.sleep(2)
            continue
        break

    check_response(response)
    click.echo(
        click.style("Custom WAF is now associated with ", fg="green")
        + click.style(f"{elb_name} ", fg="white", bold=True)
        + click.style("for domain ", fg="green")
        + click.style(f"{domain_name}", fg="white", bold=True),
    )


if __name__ == "__main__":
    waf()
