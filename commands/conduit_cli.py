import os
import subprocess
import time

import boto3
import click

from commands.utils import check_aws_conn

CONDUIT_DOCKER_IMAGE_LOCATION = "public.ecr.aws/uktrade/tunnel"


def get_cluster_arn(app: str, env: str) -> str:
    client = boto3.client("resourcegroupstaggingapi")

    response = client.get_resources(
        TagFilters=[
            {"Key": "copilot-application", "Values": [app]},
            {"Key": "copilot-environment", "Values": [env]},
            {"Key": "aws:cloudformation:logical-id", "Values": ["Cluster"]},
        ]
    )

    return response["ResourceTagMappingList"][0]["ResourceARN"]


def create_task(app: str, env: str, secret_arn: str) -> None:
    command = f"copilot task run -n dbtunnel --image {CONDUIT_DOCKER_IMAGE_LOCATION} --secrets DB_SECRET={secret_arn} --app {app} --env {env}"
    subprocess.call(command, shell=True)


def get_postgres_secret_arn(app: str, env: str) -> str:
    secret_name = f"/copilot/{app}/{env}/secrets/POSTGRES"

    return boto3.client("secretsmanager").get_secret_value(SecretId=secret_name)["ARN"]


def is_task_running(cluster_arn: str) -> bool:
    tasks = boto3.client("ecs").list_tasks(cluster=cluster_arn, desiredStatus="RUNNING", family="copilot-dbtunnel")

    try:
        if tasks["taskArns"]:
            return True
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
            f"Attempt to exec into running task timed out. Try again by running `copilot task exec --app {app} --env {env} or check status of task in Amazon ECS console."
        )


@click.group()
def conduit():
    pass


@conduit.command()
@click.option("--project-profile", required=True, help="AWS account profile name")
@click.option("--app", help="AWS application name", required=True)
@click.option("--env", help="AWS environment name", required=True)
def tunnel(project_profile: str, app: str, env: str) -> None:
    check_aws_conn(project_profile)

    try:
        cluster_arn = get_cluster_arn(app, env)
    except IndexError:
        click.secho(f"No cluster resource found with tag filter values {app} and {env}", fg="red")
        exit()

    if not is_task_running(cluster_arn):
        try:
            secret_arn = get_postgres_secret_arn(app, env)
        except boto3.client("secretsmanager").exceptions.ResourceNotFoundException:
            click.secho(f"No secret found matching application {app} and environment {env}.")
            exit()

        create_task(app, env, secret_arn)

    exec_into_task(app, env, cluster_arn)
