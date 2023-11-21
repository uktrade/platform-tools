import json
import re
import subprocess
import time

import click

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


def create_addon_client_task(app: Application, env: str, addon_type: str, addon_name: str):
    connection_secret_arn = get_connection_secret_arn(app, env, addon_name.upper())

    subprocess.call(
        f"copilot task run --app {app.name} --env {env} "
        f"--task-group-name conduit-{app.name}-{env}-{normalise_string(addon_name)} "
        f"--image {CONDUIT_DOCKER_IMAGE_LOCATION}:{addon_type} "
        f"--secrets CONNECTION_SECRET={connection_secret_arn} "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


def addon_client_is_running(app: Application, env: str, cluster_arn: str, addon_name: str) -> bool:
    ecs_client = app.environments[env].session.client("ecs")

    tasks = ecs_client.list_tasks(
        cluster=cluster_arn,
        desiredStatus="RUNNING",
        family=f"copilot-conduit-{app.name}-{env}-{normalise_string(addon_name)}",
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


def connect_to_addon_client_task(app: Application, env: str, cluster_arn: str, addon_name: str):
    tries = 0
    running = False

    while tries < 15 and not running:
        tries += 1

        if addon_client_is_running(app, env, cluster_arn, addon_name):
            running = True
            subprocess.call(
                "copilot task exec "
                f"--app {app.name} --env {env} "
                f"--name conduit-{app.name}-{env}-{normalise_string(addon_name)} "
                f"--command bash",
                shell=True,
            )

        time.sleep(1)

    if not running:
        raise CreateTaskTimeoutConduitError


def add_stack_delete_policy_to_task_role(app: Application, env: str, addon_name: str):
    session = app.environments[env].session
    cloudformation_client = session.client("cloudformation")
    iam_client = session.client("iam")

    conduit_stack_name = f"task-conduit-{app.name}-{env}-{normalise_string(addon_name)}"
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


def start_conduit(app: str, env: str, addon_type: str, addon_name: str = None):
    if addon_type not in CONDUIT_ADDON_TYPES:
        raise InvalidAddonTypeConduitError(addon_type)

    application = load_application(app)
    cluster_arn = get_cluster_arn(application, env)
    addon_name = addon_name or addon_type

    if not addon_client_is_running(application, env, cluster_arn, addon_name):
        create_addon_client_task(application, env, addon_type, addon_name)
        add_stack_delete_policy_to_task_role(application, env, addon_name)

    connect_to_addon_client_task(application, env, cluster_arn, addon_name)


@click.command(cls=ClickDocOptCommand)
@click.argument("addon_type", type=click.Choice(CONDUIT_ADDON_TYPES))
@click.option("--app", help="AWS application name", required=True)
@click.option("--env", help="AWS environment name", required=True)
@click.option("--addon-name", help="Name of custom addon", required=False)
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
