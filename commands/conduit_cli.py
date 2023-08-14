import json
import os
import subprocess
import time

import boto3
import click

from commands.utils import check_aws_conn

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


def get_postgres_secret(app: str, env: str, name: str = "POSTGRES"):
    secret_name = f"/copilot/{app}/{env}/secrets/{name}"

    return boto3.client("secretsmanager").get_secret_value(SecretId=secret_name)


def create_task(app: str, env: str, db_secret: str = "POSTGRES") -> None:
    secret = get_postgres_secret(app, env, db_secret)
    secret_arn = secret["ARN"]
    secret_json = json.loads(secret["SecretString"])
    postgres_password = secret_json["password"]
    command = f"copilot task run -n dbtunnel --image {CONDUIT_DOCKER_IMAGE_LOCATION} --secrets DB_SECRET={secret_arn} --env-vars POSTGRES_PASSWORD={postgres_password} --app {app} --env {env}"

    subprocess.call(command, shell=True)


def is_task_running(cluster_arn: str) -> bool:
    tasks = boto3.client("ecs").list_tasks(cluster=cluster_arn, desiredStatus="RUNNING", family="copilot-dbtunnel")

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


def exec_into_task(app: str, env: str, cluster_arn: str) -> None:
    # There is a delay between a task's being created and its health status changing from PROVISIONING to RUNNING,
    # so we need to wait before running the exec command or timeout if taking too long.
    timeout = time.time() + 60
    connected = False
    while time.time() < timeout:
        if is_task_running(cluster_arn):
            os.system(f"copilot task exec --app {app} --env {env}")
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
@click.option("--app", help="AWS application name", required=True)
@click.option("--env", help="AWS environment name", required=True)
@click.option("--db-secret", help="DB Credentials secret name", required=True, default="POSTGRES")
def tunnel(project_profile: str, app: str, env: str, db_secret: str) -> None:
    check_aws_conn(project_profile)

    cluster_arn = get_cluster_arn(app, env)
    if not cluster_arn:
        click.secho(f"No cluster resource found with tag filter values {app} and {env}", fg="red")
        exit()

    if not is_task_running(cluster_arn):
        try:
            create_task(app, env, db_secret)
        except boto3.client("secretsmanager").exceptions.ResourceNotFoundException:
            click.secho(f"No secret found matching application {app} and environment {env}.")
            exit()

    exec_into_task(app, env, cluster_arn)
