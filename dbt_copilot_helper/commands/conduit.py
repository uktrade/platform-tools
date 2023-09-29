import re
import subprocess
import time

import boto3
import click

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


def get_cluster_arn(app: str, env: str) -> str:
    ecs_client = boto3.client("ecs")

    for cluster_arn in ecs_client.list_clusters()["clusterArns"]:
        tags_response = ecs_client.list_tags_for_resource(resourceArn=cluster_arn)
        tags = tags_response["tags"]

        app_key_found = False
        env_key_found = False
        cluster_key_found = False

        for tag in tags:
            if tag["key"] == "copilot-application" and tag["value"] == app:
                app_key_found = True
            if tag["key"] == "copilot-environment" and tag["value"] == env:
                env_key_found = True
            if tag["key"] == "aws:cloudformation:logical-id" and tag["value"] == "Cluster":
                cluster_key_found = True

        if app_key_found and env_key_found and cluster_key_found:
            return cluster_arn

    raise NoClusterConduitError


def get_connection_secret_arn(app: str, env: str, name: str) -> str:
    connection_secret_id = f"/copilot/{app}/{env}/secrets/{name}"

    secrets_manager = boto3.client("secretsmanager")
    ssm = boto3.client("ssm")

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


def create_addon_client_task(app: str, env: str, addon_type: str, addon_name: str):
    connection_secret_arn = get_connection_secret_arn(app, env, addon_name.upper())

    subprocess.call(
        f"copilot task run --app {app} --env {env} "
        f"--task-group-name conduit-{app}-{env}-{normalise_string(addon_name)} "
        f"--image {CONDUIT_DOCKER_IMAGE_LOCATION}:{addon_type} "
        f"--secrets CONNECTION_SECRET={connection_secret_arn} "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


def addon_client_is_running(app: str, env: str, cluster_arn: str, addon_name: str) -> bool:
    tasks = boto3.client("ecs").list_tasks(
        cluster=cluster_arn,
        desiredStatus="RUNNING",
        family=f"copilot-conduit-{app}-{env}-{normalise_string(addon_name)}",
    )

    if not tasks["taskArns"]:
        return False

    described_tasks = boto3.client("ecs").describe_tasks(
        cluster=cluster_arn, tasks=tasks["taskArns"]
    )

    # The ExecuteCommandAgent often takes longer to start running than the task and without the
    # agent it's not possible to exec into a task.
    for task in described_tasks["tasks"]:
        for container in task["containers"]:
            for agent in container["managedAgents"]:
                if agent["name"] == "ExecuteCommandAgent" and agent["lastStatus"] == "RUNNING":
                    return True

    return False


def connect_to_addon_client_task(app: str, env: str, cluster_arn: str, addon_name: str):
    tries = 0
    running = False

    while tries < 15 and not running:
        tries += 1

        if addon_client_is_running(app, env, cluster_arn, addon_name):
            running = True
            subprocess.call(
                "copilot task exec "
                f"--app {app} --env {env} "
                f"--name conduit-{app}-{env}-{normalise_string(addon_name)} "
                f"--command bash",
                shell=True,
            )

        time.sleep(1)

    if not running:
        raise CreateTaskTimeoutConduitError


def start_conduit(app: str, env: str, addon_type: str, addon_name: str = None):
    if addon_type not in CONDUIT_ADDON_TYPES:
        raise InvalidAddonTypeConduitError(addon_type)

    cluster_arn = get_cluster_arn(app, env)
    addon_name = addon_name or addon_type

    if not addon_client_is_running(app, env, cluster_arn, addon_name):
        create_addon_client_task(app, env, addon_type, addon_name)
    connect_to_addon_client_task(app, env, cluster_arn, addon_name)


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
