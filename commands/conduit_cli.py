import subprocess
import time

import boto3
import click


class ConduitError(Exception):
    pass


class NoClusterConduitError(ConduitError):
    pass


class NoConnectionSecretError(ConduitError):
    pass


class TaskConnectionTimeoutError(ConduitError):
    pass


CONDUIT_DOCKER_IMAGE_LOCATION = "public.ecr.aws/uktrade/tunnel"


def get_cluster_arn(app: str, env: str) -> str:
    ecs_client = boto3.client("ecs")

    for cluster_arn in ecs_client.list_clusters()["clusterArns"]:
        # Describe the tags for the cluster
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
        return secrets_manager.describe_secret(SecretId=connection_secret_id)["ARN"]
    except secrets_manager.exceptions.ResourceNotFoundException:
        pass

    try:
        return ssm.get_parameter(Name=connection_secret_id, WithDecryption=False)["Parameter"]["ARN"]
    except ssm.exceptions.ParameterNotFound:
        pass

    raise NoConnectionSecretError


def create_addon_client_task(app: str, env: str, addon_type: str, addon_name: str = None):
    connection_secret_arn = get_connection_secret_arn(app, env, (addon_name or addon_type).upper())

    subprocess.call(
        f"copilot task run --app {app} --env {env} --name conduit-{addon_type} "
        f"--image {CONDUIT_DOCKER_IMAGE_LOCATION}:{addon_type} "
        f"--secrets CONNECTION_SECRET={connection_secret_arn}",
        shell=True,
    )


def addon_client_is_running(cluster_arn: str, addon_type: str) -> bool:
    tasks = boto3.client("ecs").list_tasks(
        cluster=cluster_arn,
        desiredStatus="RUNNING",
        family=f"copilot-conduit-{addon_type}",
    )

    described_tasks = boto3.client("ecs").describe_tasks(cluster=cluster_arn, tasks=tasks["taskArns"])

    # The ExecuteCommandAgent often takes longer to start running than the task and without the
    # agent it's not possible to exec into a task.
    for task in described_tasks["tasks"]:
        for container in task["containers"]:
            for agent in container["managedAgents"]:
                if agent["name"] == "ExecuteCommandAgent" and agent["lastStatus"] == "RUNNING":
                    return True

    return False


# connect_to_addon_client_task(app:str, env: str, cluster_arn: str, addon_type: str)
#   wait until the client task is started and managed agent running
#   subprocess.call(f"copilot task exec --app {app} --env {env} --name conduit-{addon_type}", shell=True)
#
# tests:
#   - test subprocess.call executed when addon_client_is_running == True
#   - test subprocess.call not executed when addon_client_is_running == False and exception raised


def connect_to_addon_client_task(app: str, env: str, cluster_arn: str, addon_type: str):
    tries = 0
    running = False

    while tries < 15 and not running:
        tries += 1

        if addon_client_is_running(cluster_arn, addon_type):
            running = True
            subprocess.call(f"copilot task exec --app {app} --env {env} --name conduit-{addon_type}", shell=True)

        time.sleep(1)

    if not running:
        raise TaskConnectionTimeoutError


# commands: postgres, redis, opensearch
# tests:
#   happy path --addon-name not specified
#   - test that get_cluster_arn is called
#   - test that create_addon_client_task is called without an addon_name
#   - test that get_connection_secret is called with addon_type
#   - test that addon_client_is_running is called with addon_type
#   - test that connect_to_addon_client_task is called with addon_type
#   happy path --addon-name specified
#   - test that get_cluster_arn is called
#   - test that create_addon_client_task is called with an addon_name
#   - test that get_connection_secret is called with addon_name
#   - test that addon_client_is_running is called with addon_type
#   - test that connect_to_addon_client_task is called with addon_type
#  sad path no cluster exists
#   - test that get_cluster_arn is called
#   - test that "no cluster for app or env exists" is logged
#   - test that command exits with non-zero code
#  sad path no secret exists --addon-name not specified
#   - test that get_connection_secret_arn is called with addon_type
#   - test that "no connection string for addon exists" is logged
#   - test that command exits with non-zero code
#  sad path no secret exists --addon-name specified
#   - test that get_connection_secret_arn is called with addon_name
#   - test that "no connection string for addon exists" is logged
#   - test that command exits with non-zero code
#  sad path task fails to start
#   - test that addon_client_is_running is called x times
#   - test that "addon client failed to start, check logs" is logged (should we print logs?)
#   - test that command exits with non-zero code


# def get_cluster_arn(app: str, env: str) -> str:
#     ecs_client = boto3.client("ecs")
#
#     for cluster_arn in ecs_client.list_clusters()["clusterArns"]:
#         # Describe the tags for the cluster
#         tags_response = ecs_client.list_tags_for_resource(resourceArn=cluster_arn)
#         tags = tags_response["tags"]
#
#         app_key_found = False
#         env_key_found = False
#         cluster_key_found = False
#
#         for tag in tags:
#             if tag["key"] == "copilot-application" and tag["value"] == app:
#                 app_key_found = True
#             if tag["key"] == "copilot-environment" and tag["value"] == env:
#                 env_key_found = True
#             if tag["key"] == "aws:cloudformation:logical-id" and tag["value"] == "Cluster":
#                 cluster_key_found = True
#
#         if app_key_found and env_key_found and cluster_key_found:
#             return cluster_arn
#
#
# def get_secret_arn(app: str, env: str, name: str):
#     secret_name = f"/copilot/{app}/{env}/secrets/{name}"
#
#     return boto3.client("secretsmanager").describe_secret(SecretId=secret_name)['ARN']
#
#
# def get_postgres_secret(app: str, env: str, name: str):
#     secret_name = f"/copilot/{app}/{env}/secrets/{name}"
#
#     return boto3.client("secretsmanager").get_secret_value(SecretId=secret_name)
#
#
# def create_task(app: str, env: str, conduit_settings: dict[str, str], secret_name: str) -> None:
#     secret_arn = get_secret_arn(app, env, secret_name)
#
#     command = (f"copilot task run --name conduit-{conduit_settings['task_name']} "
#                f"--image {CONDUIT_DOCKER_IMAGE_LOCATION}:{conduit_settings['docker_image_tag']} "
#                f"--secrets DB_SECRET={secret_arn} --app {app} --env {env}")
#
#     subprocess.call(command, shell=True)
#
#
# def get_running_tasks(cluster_arn: str, connection_type: str) -> list[tuple[str, str]]:
#     tasks = boto3.client("ecs").list_tasks(
#         cluster=cluster_arn, desiredStatus="RUNNING", family=f"copilot-conduit-{connection_type}"
#     )
#
#     try:
#         if tasks["taskArns"]:
#             running_tasks = []
#
#             described_tasks = boto3.client("ecs").describe_tasks(cluster=cluster_arn, tasks=tasks["taskArns"])
#
#             # The ExecuteCommandAgent often takes longer to start running than the task and without the
#             # agent it's not possible to exec into a task.
#             for task in described_tasks["tasks"]:
#                 for container in task['containers']:
#                     for agent in container["managedAgents"]:
#                         if agent["name"] == "ExecuteCommandAgent":
#                             running_tasks.append(())
#                             agent_running = agent["lastStatus"] == "RUNNING"
#
#             # return described_tasks["tasks"][0]["lastStatus"] == "RUNNING" and agent_running
#             return running_tasks
#
#     except ValueError:
#         return []
#
#
# def is_task_running(cluster_arn: str, connection_type: str) -> list[tuple[str, str]]:
#     tasks = get_running_tasks(cluster_arn, connection_type)
#
#     try:
#         if tasks["taskArns"]:
#             running_tasks = []
#
#             described_tasks = boto3.client("ecs").describe_tasks(cluster=cluster_arn, tasks=tasks["taskArns"])
#             agent_running = False
#
#             # The ExecuteCommandAgent often takes longer to start running than the task and without the agent it's not possible to exec into a task.
#             for agent in described_tasks["tasks"][0]["containers"][0]["managedAgents"]:
#                 if agent["name"] == "ExecuteCommandAgent" and agent["lastStatus"] == "RUNNING":
#                     agent_running = True
#
#             # return described_tasks["tasks"][0]["lastStatus"] == "RUNNING" and agent_running
#             return running_tasks
#
#     except ValueError:
#         return False
#
#
# def exec_into_task(app: str, env: str, cluster_arn: str) -> None:
#     # There is a delay between a task's being created and its health status changing from PROVISIONING to RUNNING,
#     # so we need to wait before running the exec command or timeout if taking too long.
#     timeout = time.time() + 60
#     connected = False
#     while time.time() < timeout:
#         if is_task_running(cluster_arn):
#             os.system(f"copilot task exec --app {app} --env {env}")  # execution pauses until session end
#             connected = True
#             break
#
#     if connected == False:
#         print(
#             f"Attempt to exec into running task timed out. Try again by running `copilot task exec --app {app} --env {env}` or check status of task in Amazon ECS console."
#         )
#
#
# def create_conduit_tunnel(project_profile: str, app: str, env: str, connection_type: str, secret_name: str):
#     check_aws_conn(project_profile)
#
#     conduit_settings = CONDUIT_SETTINGS[connection_type]
#
#     connection_secret_name = secret_name if secret_name is not None else conduit_settings['default_secret_name']
#
#     cluster_arn = get_cluster_arn(app, env)
#     if not cluster_arn:
#         click.secho(f"No cluster resource found with tag filter values {app} and {env}", fg="red")
#         exit()
#
#     running_tasks = get_running_tasks(cluster_arn, connection_type)
#
#     if len(running_tasks):
#         click.secho(f"There are currently {len(running_tasks)} {connection_type} conduits running for "
#                     f"application {app} and environment {env}, you may want to clean them up.", fg="yellow")
#
#     try:
#         create_task(app, env, conduit_settings, connection_secret_name)
#     except boto3.client("secretsmanager").exceptions.ResourceNotFoundException:
#         click.secho(f"No secret found matching application {app} and environment {env}.")
#         exit()
#
#     exec_into_task(app, env, cluster_arn, conduit_settings)


@click.group()
def conduit():
    pass


@conduit.command()
@click.option("--project-profile", required=True, help="AWS account profile name")
@click.option("--app", help="AWS application name", required=True)
@click.option("--env", help="AWS environment name", required=True)
@click.option("--secret-name", help="Name of a custom connection secret to inject", required=False)
def postgres(project_profile: str, app: str, env: str, secret_name: str):
    # create_conduit_tunnel(project_profile, app, env, 'postgres', secret_name)
    pass


@conduit.command()
@click.option("--project-profile", required=True, help="AWS account profile name")
@click.option("--app", help="AWS application name", required=True)
@click.option("--env", help="AWS environment name", required=True)
@click.option("--secret-name", help="Name of a custom connection secret to inject", required=False)
def redis(project_profile: str, app: str, env: str, secret_name: str):
    # create_conduit_tunnel(project_profile, app, env, 'redis', secret_name)
    pass


@conduit.command()
@click.option("--project-profile", required=True, help="AWS account profile name")
@click.option("--app", help="AWS application name", required=True)
@click.option("--env", help="AWS environment name", required=True)
@click.option("--secret-name", help="Name of a custom connection secret to inject", required=False)
def opensearch(project_profile: str, app: str, env: str, secret_name: str):
    # create_conduit_tunnel(project_profile, app, env, 'opensearch', secret_name)
    pass


# @conduit.command()
# @click.option("--project-profile", required=True, help="AWS account profile name")
# @click.option("--app", help="AWS application name", required=True)
# @click.option("--env", help="AWS environment name", required=True)
# @click.option("--db-secret-name", help="Database credentials secret name", required=True, default="POSTGRES")
# def tunnel(project_profile: str, app: str, env: str, db_secret_name: str) -> None:
#     check_aws_conn(project_profile)
#
#     cluster_arn = get_cluster_arn(app, env)
#     if not cluster_arn:
#         click.secho(f"No cluster resource found with tag filter values {app} and {env}", fg="red")
#         exit()
#
#     if not is_task_running(cluster_arn):
#         try:
#             create_task(app, env, db_secret_name)
#         except boto3.client("secretsmanager").exceptions.ResourceNotFoundException:
#             click.secho(f"No secret found matching application {app} and environment {env}.")
#             exit()
#
#     exec_into_task(app, env, cluster_arn)
