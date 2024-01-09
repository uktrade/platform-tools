import json
import random
import re
import string
import subprocess
import time

import click
from cfn_tools import dump_yaml
from cfn_tools import load_yaml

from dbt_copilot_helper.utils.application import Application
from dbt_copilot_helper.utils.application import load_application
from dbt_copilot_helper.utils.click import ClickDocOptCommand
from dbt_copilot_helper.utils.versioning import (
    check_copilot_helper_version_needs_update,
)


class ConduitError(Exception):
    pass


class InvalidAddonTypeConduitError(ConduitError):
    pass


class NoClusterConduitError(ConduitError):
    pass


class SecretNotFoundConduitError(ConduitError):
    pass


class CreateTaskTimeoutConduitError(ConduitError):
    pass


CONDUIT_DOCKER_IMAGE_LOCATION = "public.ecr.aws/uktrade/tunnel"
CONDUIT_ADDON_TYPES = [
    "opensearch",
    "postgres",
    "redis",
]


def normalise_string(to_normalise: str) -> str:
    output = re.sub("[^0-9a-zA-Z]+", "-", to_normalise)
    return output.lower()


def get_or_create_task_name(app: Application, env: str, addon_name: str) -> str:
    ssm = app.environments[env].session.client("ssm")
    task_name_parameter = f"/copilot/{app.name}/{env}/conduits/{addon_name}_CONDUIT_TASK_NAME"

    try:
        return ssm.get_parameter(Name=task_name_parameter)["Parameter"]["Value"]
    except ssm.exceptions.ParameterNotFound:
        random_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        return f"conduit-{app.name}-{env}-{normalise_string(addon_name)}-{random_id}"


def get_cluster_arn(app: Application, env: str) -> str:
    ecs_client = app.environments[env].session.client("ecs")

    for cluster_arn in ecs_client.list_clusters()["clusterArns"]:
        tags_response = ecs_client.list_tags_for_resource(resourceArn=cluster_arn)
        tags = tags_response["tags"]

        app_key_found = False
        env_key_found = False
        cluster_key_found = False

        for tag in tags:
            if tag["key"] == "copilot-application" and tag["value"] == app.name:
                app_key_found = True
            if tag["key"] == "copilot-environment" and tag["value"] == env:
                env_key_found = True
            if tag["key"] == "aws:cloudformation:logical-id" and tag["value"] == "Cluster":
                cluster_key_found = True

        if app_key_found and env_key_found and cluster_key_found:
            return cluster_arn

    raise NoClusterConduitError


def get_connection_secret_arn(app: Application, env: str, name: str) -> str:
    secrets_manager = app.environments[env].session.client("secretsmanager")
    ssm = app.environments[env].session.client("ssm")

    connection_secret_id = f"/copilot/{app.name}/{env}/secrets/{name}"

    try:
        return ssm.get_parameter(Name=connection_secret_id, WithDecryption=False)["Parameter"][
            "ARN"
        ]
    except ssm.exceptions.ParameterNotFound:
        pass

    try:
        return secrets_manager.describe_secret(SecretId=connection_secret_id)["ARN"]
    except secrets_manager.exceptions.ResourceNotFoundException:
        pass

    raise SecretNotFoundConduitError(name)


def create_addon_client_task(
    app: Application, env: str, addon_type: str, addon_name: str, task_name: str
):
    connection_secret_arn = get_connection_secret_arn(app, env, addon_name.upper())

    subprocess.call(
        f"copilot task run --app {app.name} --env {env} "
        f"--task-group-name {task_name} "
        f"--image {CONDUIT_DOCKER_IMAGE_LOCATION}:{addon_type} "
        f"--secrets CONNECTION_SECRET={connection_secret_arn} "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


def addon_client_is_running(app: Application, env: str, cluster_arn: str, task_name: str) -> bool:
    ecs_client = app.environments[env].session.client("ecs")

    tasks = ecs_client.list_tasks(
        cluster=cluster_arn,
        desiredStatus="RUNNING",
        family=f"copilot-{task_name}",
    )

    if not tasks["taskArns"]:
        return False

    described_tasks = ecs_client.describe_tasks(cluster=cluster_arn, tasks=tasks["taskArns"])

    # The ExecuteCommandAgent often takes longer to start running than the task and without the
    # agent it's not possible to exec into a task.
    for task in described_tasks["tasks"]:
        for container in task["containers"]:
            for agent in container["managedAgents"]:
                if agent["name"] == "ExecuteCommandAgent" and agent["lastStatus"] == "RUNNING":
                    return True

    return False


def connect_to_addon_client_task(app: Application, env: str, cluster_arn: str, task_name: str):
    tries = 0
    running = False

    while tries < 15 and not running:
        tries += 1

        if addon_client_is_running(app, env, cluster_arn, task_name):
            running = True
            subprocess.call(
                "copilot task exec "
                f"--app {app.name} --env {env} "
                f"--name {task_name} "
                f"--command bash",
                shell=True,
            )

        time.sleep(1)

    if not running:
        raise CreateTaskTimeoutConduitError


def add_stack_delete_policy_to_task_role(app: Application, env: str, task_name: str):
    session = app.environments[env].session
    cloudformation_client = session.client("cloudformation")
    iam_client = session.client("iam")

    conduit_stack_name = f"task-{task_name}"
    conduit_stack_resources = cloudformation_client.list_stack_resources(
        StackName=conduit_stack_name
    )["StackResourceSummaries"]

    for resource in conduit_stack_resources:
        if resource["LogicalResourceId"] == "DefaultTaskRole":
            task_role_name = resource["PhysicalResourceId"]
            iam_client.put_role_policy(
                RoleName=task_role_name,
                PolicyName="DeleteCloudFormationStack",
                PolicyDocument=json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Action": ["cloudformation:DeleteStack"],
                                "Effect": "Allow",
                                "Resource": f"arn:aws:cloudformation:*:*:stack/{conduit_stack_name}/*",
                            },
                        ],
                    },
                ),
            )


def update_conduit_stack_resources(
    app: Application, env: str, addon_type: str, addon_name: str, task_name: str
):
    session = app.environments[env].session
    cloudformation_client = session.client("cloudformation")

    conduit_stack_name = f"task-{task_name}"
    template = cloudformation_client.get_template(StackName=conduit_stack_name)
    template_yml = load_yaml(template["TemplateBody"])
    template_yml["Resources"]["LogGroup"]["DeletionPolicy"] = "Retain"
    template_yml["Resources"]["TaskNameParameter"] = load_yaml(
        f"""
        Type: AWS::SSM::Parameter
        Properties:
          Name: /copilot/{app.name}/{env}/conduits/{addon_name}_CONDUIT_TASK_NAME
          Type: String
          Value: {task_name}
        """
    )

    iam_client = session.client("iam")
    log_filter_role_arn = iam_client.get_role(RoleName="CWLtoSubscriptionFilterRole")["Role"]["Arn"]

    ssm_client = session.client("ssm")
    destination_log_group_arns = json.loads(
        ssm_client.get_parameter(Name="/copilot/tools/central_log_groups")["Parameter"]["Value"]
    )

    destination_arn = destination_log_group_arns["dev"]
    if env.lower() in ("prod", "production"):
        destination_arn = destination_log_group_arns["prod"]

    template_yml["Resources"]["SubscriptionFilter"] = load_yaml(
        f"""
        Type: AWS::Logs::SubscriptionFilter
        DeletionPolicy: Retain
        Properties:
          RoleArn: {log_filter_role_arn}
          LogGroupName: /copilot/{task_name}
          FilterName: /copilot/conduit/{app.name}/{env}/{addon_type}/{normalise_string(addon_name)}/{task_name.rsplit("-", 1)[1]}
          FilterPattern: ''
          DestinationArn: {destination_arn}
        """
    )

    params = []
    if "Parameters" in template_yml:
        for param in template_yml["Parameters"]:
            params.append({"ParameterKey": param, "UsePreviousValue": True})

    cloudformation_client.update_stack(
        StackName=conduit_stack_name,
        TemplateBody=dump_yaml(template_yml),
        Parameters=params,
        Capabilities=["CAPABILITY_IAM"],
    )


def start_conduit(app: str, env: str, addon_type: str, addon_name: str = None):
    if addon_type not in CONDUIT_ADDON_TYPES:
        raise InvalidAddonTypeConduitError(addon_type)

    application = load_application(app)
    cluster_arn = get_cluster_arn(application, env)
    task_name = get_or_create_task_name(application, env, addon_name)

    if not addon_client_is_running(application, env, cluster_arn, task_name):
        create_addon_client_task(application, env, addon_type, addon_name, task_name)
        add_stack_delete_policy_to_task_role(application, env, task_name)
        update_conduit_stack_resources(application, env, addon_type, addon_name, task_name)

    connect_to_addon_client_task(application, env, cluster_arn, task_name)


@click.command(cls=ClickDocOptCommand)
@click.argument("addon_type", type=click.Choice(CONDUIT_ADDON_TYPES))
@click.option("--app", help="AWS application name", required=True)
@click.option("--env", help="AWS environment name", required=True)
@click.option("--addon-name", help="Name of custom addon", required=True)
def conduit(addon_type: str, app: str, env: str, addon_name: str):
    """Create a conduit connection to an addon."""
    check_copilot_helper_version_needs_update()

    try:
        start_conduit(app, env, addon_type, addon_name)
    except InvalidAddonTypeConduitError:
        click.secho(
            f"""Addon type "{addon_type}" does not exist, try one of {", ".join(CONDUIT_ADDON_TYPES)}.""",
            fg="red",
        )
        exit(1)
    except NoClusterConduitError:
        click.secho(f"""No ECS cluster found for "{app}" in "{env}" environment.""", fg="red")
        exit(1)
    except SecretNotFoundConduitError as err:
        click.secho(
            f"""No secret called "{addon_name or err}" for "{app}" in "{env}" environment.""",
            fg="red",
        )
        exit(1)
    except CreateTaskTimeoutConduitError:
        click.secho(
            f"""Client ({addon_type}) ECS task has failed to start for "{app}" in "{env}" environment.""",
            fg="red",
        )
        exit(1)
