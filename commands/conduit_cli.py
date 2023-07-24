import os
import subprocess
import time

import boto3
import click

from commands.utils import check_aws_conn


def get_cluster_arn(app, env):
    client = boto3.client("resourcegroupstaggingapi")

    response = client.get_resources(
        TagFilters=[
            {"Key": "copilot-application", "Values": [app]},
            {"Key": "copilot-environment", "Values": [env]},
            {"Key": "aws:cloudformation:logical-id", "Values": ["Cluster"]},
        ]
    )

    return response["ResourceTagMappingList"][0]["ResourceARN"]


def create_task(app, env, secret_arn):
    command = f"copilot task run -n dbtunnel --dockerfile Dockerfile --secrets DB_SECRET={secret_arn} --app {app} --env {env}"
    subprocess.call(command, shell=True)


def get_postgres_secret_arn(app, env):
    secret_name = f"/copilot/{app}/{env}/secrets/POSTGRES"

    return boto3.client("secretsmanager").get_secret_value(SecretId=secret_name)["ARN"]


def is_task_running(cluster_arn):
    tasks = boto3.client("ecs").list_tasks(cluster=cluster_arn, desiredStatus="RUNNING", family="copilot-dbtunnel")

    try:
        return tasks["taskArns"]
    except ValueError:
        return False


def exec_into_task(app, env, cluster_arn):
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
@click.option("--project-profile", required=True, help="aws account profile name")
@click.option("--app", help="aws app name", required=True)
@click.option("--env", help="aws environment name", required=True)
def tunnel(project_profile, app, env):
    check_aws_conn(project_profile)

    try:
        cluster_arn = get_cluster_arn(app, env)
    except IndexError:
        click.secho(f"No cluster resource found with tag filter values {app} and {env}", fg="red")
        exit()

    if not is_task_running(cluster_arn):
        secret_arn = get_postgres_secret_arn(app, env)
        create_task(app, env, secret_arn)

    exec_into_task(app, env, cluster_arn)
