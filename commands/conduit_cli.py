import json
import os
import subprocess
import time

import boto3
import botocore  # noqa
import click

from commands.utils import check_aws_conn

CONDUIT_IMAGE_LOCATIONS = {
    "postgres": "public.ecr.aws/uktrade/tunnel-postgres",
    "redis": "public.ecr.aws/uktrade/tunnel-redis",
}


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


def get_postgres_secret(app: str, env: str, name: str):
    secret_name = f"/copilot/{app}/{env}/secrets/{name}"

    return boto3.client("secretsmanager").get_secret_value(SecretId=secret_name)


def update_postgres_command(app: str, env: str, command: str, secret_name: str) -> str:
    secret = get_postgres_secret(app, env, secret_name)
    secret_arn = secret["ARN"]
    secret_json = json.loads(secret["SecretString"])
    postgres_password = secret_json["password"]

    return f"{command} --secrets DB_SECRET={secret_arn} --env-vars POSTGRES_PASSWORD={postgres_password}"


def create_task(app: str, env: str, addon_type: str, secret_name: str) -> None:
    command = f"copilot task run -n tunnel-{addon_type} --image {CONDUIT_IMAGE_LOCATIONS[addon_type]} --app {app} --env {env}"
    if addon_type == "postgres":
        command = update_postgres_command(app, env, command, secret_name)

    subprocess.call(command, shell=True)


def is_task_running(cluster_arn: str, addon_type: str) -> bool:
    tasks = boto3.client("ecs").list_tasks(
        cluster=cluster_arn, desiredStatus="RUNNING", family=f"copilot-tunnel-{addon_type}"
    )

    try:
        if tasks["taskArns"]:
            described_tasks = boto3.client("ecs").describe_tasks(cluster=cluster_arn, tasks=tasks["taskArns"])
            agent_running = False

            # The ExecuteCommandAgent often takes longer to start running than the task and without the agent it's not possible to exec into a task.
            for agent in described_tasks["tasks"][0]["containers"][0]["managedAgents"]:
                if agent["name"] == "ExecuteCommandAgent" and agent["lastStatus"] == "RUNNING":
                    agent_running = True

            return described_tasks["tasks"][0]["lastStatus"] == "RUNNING" and agent_running

    except ValueError:
        return False


def get_redis_cluster(app: str, env: str):
    elasticache = boto3.client("elasticache")
    resource_tagging = boto3.client("resourcegroupstaggingapi")
    clusters = elasticache.describe_cache_clusters(ShowCacheNodeInfo=True)["CacheClusters"]
    desired_tags = {"copilot-application": app, "copilot-environment": env}

    for cluster in clusters:
        tags = resource_tagging.get_resources(ResourceARNList=[cluster["ARN"]])["ResourceTagMappingList"][0]["Tags"]
        tag_dict = {tag["Key"]: tag["Value"] for tag in tags}

        # Check if desired tags are a subset of the cluster's tags
        if desired_tags.items() <= tag_dict.items():
            return cluster


def get_postgres_command(app: str, env: str, secret_name: str):
    secret = get_postgres_secret(app, env, secret_name)
    secret_json = json.loads(secret["SecretString"])
    connection_string = f"postgres://{secret_json['username']}:{secret_json['password']}@{secret_json['host']}:5432/{secret_json['dbname']}"

    return f"psql {connection_string}"


def get_redis_command(app: str, env: str):
    cluster = get_redis_cluster(app, env)
    if not cluster:
        click.secho(f"No cluster resource found with tag filter values {app} and {env}", fg="red")
        exit()

    address = cluster["CacheNodes"][0]["Endpoint"]["Address"]
    port = cluster["CacheNodes"][0]["Endpoint"]["Port"]

    return f"redis-cli -c -h {address} --tls -p {port}"


def get_addon_command(app: str, env: str, addon_type: str, secret_name: str = "POSTGRES") -> str:
    if addon_type == "postgres":
        return get_postgres_command(app, env, secret_name)

    if addon_type == "redis":
        return get_redis_command(app, env)


def exec_into_task(app: str, env: str, cluster_arn: str, addon_type: str, secret_name: str = "POSTGRES") -> None:
    # There is a delay between a task's being created and its health status changing from PROVISIONING to RUNNING,
    # so we need to wait before running the exec command or timeout if taking too long.
    timeout = time.time() + 60
    connected = False
    while time.time() < timeout:
        if is_task_running(cluster_arn, addon_type):
            addon_command = get_addon_command(app, env, addon_type, secret_name)
            os.system(f"copilot task exec --app {app} --env {env} --command '{addon_command}'")
            connected = True
            break

    if connected == False:
        print(
            f"Attempt to exec into running task timed out. Try again by running `copilot task exec --app {app} --env {env}` or check status of task in Amazon ECS console."
        )


@click.group()
def conduit():
    pass


@conduit.command()
@click.option("--project-profile", required=True, help="AWS account profile name")
@click.option("--app", help="AWS Copilot application name", required=True)
@click.option("--env", help="AWS Copilot environment name", required=True)
@click.option(
    "--addon-type",
    help="The addon you wish to connect to",
    type=click.Choice(["postgres", "redis"]),
    default="postgres",
    required=True,
)
@click.option("--db-secret-name", help="Database credentials secret name", required=True, default="POSTGRES")
def tunnel(
    project_profile: str, app: str, env: str, addon_type: str = "postgres", db_secret_name: str = "POSTGRES"
) -> None:
    check_aws_conn(project_profile)

    cluster_arn = get_cluster_arn(app, env)
    if not cluster_arn:
        click.secho(f"No cluster resource found with tag filter values {app} and {env}", fg="red")
        exit(1)

    if not is_task_running(cluster_arn, addon_type):
        try:
            create_task(app, env, addon_type, db_secret_name)
        except boto3.client("secretsmanager").exceptions.ResourceNotFoundException:
            click.secho(f"No secret found matching application {app} and environment {env}.")
            exit()

    exec_into_task(app, env, cluster_arn, addon_type)
