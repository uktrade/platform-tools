#!/usr/bin/env python

import re
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import time

import boto3
import click

from dbt_copilot_helper.utils.click import ClickDocOptGroup
from dbt_copilot_helper.utils.manifests import get_repository_name_from_manifest
from dbt_copilot_helper.utils.aws import get_aws_session_or_abort
from dbt_copilot_helper.utils.manifests import get_service_name_from_manifest
from dbt_copilot_helper.utils.versioning import (
    check_copilot_helper_version_needs_update,
)


@click.group(chain=True, cls=ClickDocOptGroup)
def svc():
    """AWS Copilot svc actions with DBT extras."""
    check_copilot_helper_version_needs_update()


@svc.command()
@click.option("--env", type=str, required=True)
@click.option("--name", type=str, required=True)
@click.option("--image-tag", type=str, required=False, show_default=True, default="tag-latest")
def deploy(env, name, image_tag):
    """Deploy image tag to a service, defaults to image tagged latest."""

    if image_tag == "latest":
        abort_with_message(
            f'Releasing tag "latest" is not supported. Use tag "tag-latest" instead.'
        )

    deploy_command = f"copilot svc deploy --env {env} --name {name}"

    repository_name = validate_service_manifest_and_return_repository(name)

    if repository_name != "uktrade/copilot-bootstrap":
        image_tags = get_all_tags_for_image(image_tag, repository_name)

        if image_tag == "tag-latest":
            image_tag = get_commit_tag_for_image(image_tags)
            if not image_tag:
                abort_with_message('The image tagged "tag-latest" does not have a commit tag.')

        deploy_command = f"IMAGE_TAG={image_tag} {deploy_command}"

    click.echo(f"Running: {deploy_command}")
    subprocess.call(
        deploy_command,
        shell=True,
    )


def abort_with_message(message):
    click.secho(
        message,
        fg="red",
    )
    exit(1)


def get_all_tags_for_image(image_tag_needle, repository_name):
    registry_id = boto3.client("sts").get_caller_identity()["Account"]
    ecr_client = boto3.client("ecr")
    try:
        response = ecr_client.describe_images(
            registryId=registry_id,
            repositoryName=repository_name,
            imageIds=[
                {"imageTag": image_tag_needle},
            ],
        )
        return response["imageDetails"][0]["imageTags"]
    except ecr_client.exceptions.ImageNotFoundException:
        click.secho(
            f"""No image exists with the tag "{image_tag_needle}".""",
            fg="red",
        )
        exit(1)


def get_commit_tag_for_image(image_tags_haystack):
    filtered = [tag for tag in image_tags_haystack if re.match("(commit-[a-f0-9]{7,32})", tag)]

    return filtered[0] if filtered else None


def validate_service_manifest_and_return_repository(name):
    service_manifest = Path("copilot") / name / "manifest.yml"
    try:
        service_name_in_manifest = get_service_name_from_manifest(service_manifest)
        if service_name_in_manifest != name:
            abort_with_message(
                f"Service manifest for {name} has name attribute {service_name_in_manifest}"
            )
    except FileNotFoundError:
        abort_with_message(
            f"Service manifest for {name} could not be found at path {service_manifest}"
        )

    return get_repository_name_from_manifest(service_manifest)


@svc.command()
@click.option("--env", type=str, required=True)
@click.option("--app", type=str, required=True)
@click.option("--project-profile", type=str, required=True)
def stat(env, app, project_profile):
    """Deploy image tag to a service, defaults to image tagged latest."""

    project_session = get_aws_session_or_abort(project_profile)

    click.secho(f"Showing status for app {app} in aws account {project_profile}", fg="green",)
    logs_client = project_session.client("logs")
    ecs_client = project_session.client("ecs")

    response = ecs_client.list_clusters()

    for cluster in response["clusterArns"]:
        cluster_name = cluster.split('/')[-1]
        APP = cluster_name.split('-')[0]
        ENV = cluster_name.split('-')[1]
        if app == APP and env == ENV:
            log_group_name = f"/aws/ecs/containerinsights/{cluster_name}/performance"
            break

    query_string = "stats max(CpuUtilized), max(MemoryUtilized), max(EphemeralStorageUtilized) by TaskId | filter Type='Task' | sort TaskId desc"
    date_time = datetime.now()
    end_time = int(date_time.timestamp())
    start_time = int((date_time - timedelta(minutes=5)).timestamp())
    end_time = int((date_time - timedelta(minutes=4)).timestamp())

    click.echo(
        click.style("Date & Time:  ", fg="cyan",)
        + click.style(f"{datetime.utcfromtimestamp(start_time)}", fg="cyan", bold=True)
    )

    cpu_response_id = logs_client.start_query(
        logGroupName=log_group_name,
        startTime=start_time,
        endTime=end_time,
        queryString=query_string
    )

    click.secho("waiting 5s...", fg="cyan",)
    time.sleep(5)
    cpu_response = logs_client.get_query_results(
        queryId=cpu_response_id["queryId"]
    )

    #cpu_response = {'results': [[{'field': 'TaskId', 'value': '7573108ac5d342f482c05e66a6d3eeff'}, {'field': 'max(CpuUtilized)', 'value': '18.5639'}, {'field': 'max(MemoryUtilized)', 'value': '274'}, {'field': 'max(EphemeralStorageUtilized)', 'value': '2.64'}], [{'field': 'TaskId', 'value': '97f19a10da624c8380e23647276ba001'}, {'field': 'max(CpuUtilized)', 'value': '12.3039'}, {'field': 'max(MemoryUtilized)', 'value': '275'}, {'field': 'max(EphemeralStorageUtilized)', 'value': '2.71'}], [{'field': 'TaskId', 'value': '3f6db7f58bd145c7a668f562ff896fb7'}, {'field': 'max(CpuUtilized)', 'value': '10.118'}, {'field': 'max(MemoryUtilized)', 'value': '268'}, {'field': 'max(EphemeralStorageUtilized)', 'value': '2.64'}]], 'statistics': {'recordsMatched': 3.0, 'recordsScanned': 35.0, 'bytesScanned': 29106.0}, 'status': 'Complete', 'ResponseMetadata': {'RequestId': '2c771daf-3e1f-40c2-8652-80a142b21ada', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '2c771daf-3e1f-40c2-8652-80a142b21ada', 'content-type': 'application/x-amz-json-1.1', 'content-length': '755', 'date': 'Mon, 05 Feb 2024 17:30:41 GMT'}, 'RetryAttempts': 0}}

    click.echo(
         click.style("\nName:\t", fg="green",)
         + click.style(f"{app}", fg="green", bold=True)
         )
    click.echo(
         click.style("Type:\t", fg="green",)
         + click.style("web", fg="green", bold=True)
    )
    click.echo(
         click.style("No of instances:\t", fg="green",)
         + click.style(len(cpu_response["results"]), fg="green", bold=True)
    )

    click.secho("\nTaskID\t\t\t\t\tState\t\tCPU\tMemory\tDisk", fg="cyan",)
    for task, cpu, mem, dsk in cpu_response["results"]:
        click.secho(f"{task['value']}\trunning\t\t"
                    + "%.1f" % float(cpu['value'])
                    + f"%\t{mem['value']}M\t{dsk['value']}G", fg="yellow",)
