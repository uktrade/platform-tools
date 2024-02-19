#!/usr/bin/env python

import time
from datetime import datetime
from datetime import timedelta

import click

from dbt_copilot_helper.utils.aws import get_aws_session_or_abort
from dbt_copilot_helper.utils.click import ClickDocOptGroup
from dbt_copilot_helper.utils.versioning import (
    check_copilot_helper_version_needs_update,
)


def get_query_results(env, app, profile, query_string):
    project_session = get_aws_session_or_abort(profile)

    click.secho(
        f"Showing status for app {app} in aws account {profile}",
        fg="green",
    )
    logs_client = project_session.client("logs")
    ecs_client = project_session.client("ecs")

    response = ecs_client.list_clusters()

    # Find clusters log-group
    for cluster in response["clusterArns"]:
        cluster_name = cluster.split("/")[-1]
        APP = cluster_name.split("-")[0]
        ENV = cluster_name.split("-")[1]
        if app == APP and env == ENV:
            log_group_name = f"/aws/ecs/containerinsights/{cluster_name}/performance"
            break

    # Container stats are 5 mins behind realtime.
    date_time = datetime.now()
    end_time = int(date_time.timestamp())
    start_time = int((date_time - timedelta(minutes=5)).timestamp())
    end_time = int((date_time - timedelta(minutes=4)).timestamp())

    click.echo(
        click.style("Date & Time:  ", fg="cyan")
        + click.style(f"{datetime.utcfromtimestamp(start_time)}", fg="cyan", bold=True)
    )

    # First you need to create a log query, then retrieve the log query.
    cpu_response_id = logs_client.start_query(
        logGroupName=log_group_name,
        startTime=start_time,
        endTime=end_time,
        queryString=query_string,
    )

    # Need to wait approx 5 seconds for the query to be available.
    click.secho("waiting 5s...", fg="cyan")
    time.sleep(5)

    cpu_response = logs_client.get_query_results(queryId=cpu_response_id["queryId"])

    return cpu_response


@click.group(chain=True, cls=ClickDocOptGroup)
def application():
    """Application metrics."""
    check_copilot_helper_version_needs_update()


@application.command()
@click.option("--env", type=str, required=True)
@click.option("--app", type=str, required=True)
@click.option("--project-profile", type=str, required=True)
@click.option("--storage", is_flag=True)
@click.option("--network", is_flag=True)
def stats_long(env, app, project_profile, storage, network):
    """Command to get application container level metrics."""

    # Query string to get the required container stats
    query_string = "stats max(CpuUtilized), max(MemoryUtilized) by TaskId, ContainerName, TaskDefinitionFamily, TaskDefinitionRevision, Image, StorageReadBytes, StorageWriteBytes, NetworkRxPackets, NetworkTxBytes | filter Type='Container' | sort TaskId, ContainerName desc"
    cpu_response = get_query_results(env, app, project_profile, query_string)

    click.echo(
        click.style(f"\n{'Name:':<20}", fg="green") + click.style(f"{app}", fg="green", bold=True)
    )

    click.echo(
        click.style(f"{'Environment:':<20}", fg="green")
        + click.style(f"{env}", fg="green", bold=True)
    )

    click.echo(
        click.style(f"{'No of instances:':<20}", fg="green")
        + click.style(len(cpu_response["results"]), fg="green", bold=True)
    )

    index = 0

    for field in cpu_response["results"]:
        # Not all containers have an image not present, so need to pad.
        if len(field) == 10:
            field.insert(4, {"field": "Image", "value": ""})

        task = field[0]["value"]
        cont_name = field[1]["value"]
        cont_name_short = field[2]["value"].split("-")[-1]
        task_def_revision = field[3]["value"]
        image = field[4]["value"]
        storage_read = field[5]["value"]
        storage_write = field[6]["value"]
        network_read = field[7]["value"]
        network_write = field[8]["value"]
        cpu = "%.1f%%" % float(field[9]["value"])
        memory = f"{field[10]['value']}M"

        # Nothing to compare to at start.
        if index > 0:
            end_index = index - 1
        else:
            end_index = 0

        # If its a new task then display the headings.
        if (
            index == 0
            or cpu_response["results"][index][0]["value"]
            != cpu_response["results"][end_index][0]["value"]
        ):
            click.echo(
                click.style(f"\n{'Type:':<10}", fg="green")
                + click.style(f"{cont_name_short}", fg="green", bold=True)
            )

            click.secho(f"{'Task ID:':<10}{task}", fg="green")
            heading = f"{'Container Name':<35}{'CPU':<10}{'Memory':<10}{'Revision':<12}"

            # Optional parameters.
            if storage:
                heading += f"{'Dsk Read':<12}{'Dsk Write':<12}"
            if network:
                heading += f"{'Net Read':<12}{'Net Write':<12}"
            heading += "Image"

            click.secho(heading, fg="cyan")

        # Print container stats
        result = f"{cont_name:<35}" + f"{cpu:<10}" + f"{memory:<10}" + f"{task_def_revision:<12}"

        # Optional stats.
        if storage:
            result += f"{storage_read:<12}{storage_write:<12}"
        if network:
            result += f"{network_read:<12}{network_write:<12}"
        result += f"{image}"

        click.secho(result, fg="yellow")
        index = index + 1


@application.command()
@click.option("--env", type=str, required=True)
@click.option("--app", type=str, required=True)
@click.option("--project-profile", type=str, required=True)
@click.option("--disk", is_flag=True)
@click.option("--storage", is_flag=True)
@click.option("--network", is_flag=True)
def stats(env, app, project_profile, disk, storage, network):
    """Command to get application task level metrics."""

    # Query string to get the required container stats
    query_string = "stats max(CpuUtilized), max(MemoryUtilized), max(EphemeralStorageUtilized) by TaskId, TaskDefinitionFamily, TaskDefinitionRevision, StorageReadBytes, StorageWriteBytes, NetworkRxPackets, NetworkTxBytes, KnownStatus | filter Type='Task' | sort TaskId desc"
    cpu_response = get_query_results(env, app, project_profile, query_string)

    click.echo(
        click.style(f"\n{'Name:':<20}", fg="green") + click.style(f"{app}", fg="green", bold=True)
    )

    click.echo(
        click.style(f"{'No of instances:':<20}", fg="green")
        + click.style(len(cpu_response["results"]), fg="green", bold=True)
    )

    # Add to title if additional parameters are used.
    heading = f"\n{'Type':<10}{'TaskID':<35}{'Revision':<10}{'Status':<12}{'CPU':<10}{'Memory':<10}"
    if disk:
        heading += f"{'Disk':<10}"
    if storage:
        heading += f"{'Dsk Read':<12}{'Dsk Write':<12}"
    if network:
        heading += f"{'Net Read':<12}{'Net Write':<12}"

    click.secho(heading, fg="cyan")
    for (
        task,
        taskdef,
        task_def_revision,
        storage_read,
        storage_write,
        network_read,
        network_write,
        status,
        cpu,
        memory,
        dsk,
    ) in cpu_response["results"]:
        result = (
            f"{taskdef['value'].split('-')[-1]:<10}"
            + f"{task['value']:<35}"
            + f"{task_def_revision['value']:<10}"
            + f"{status['value']:<12}"
            + f"{'%.1f' % float(cpu['value']) + '%':<10}"
            + f"{memory['value'] + 'M':<10}"
        )

        # Optional stats.
        if disk:
            result += f"{dsk['value'] + 'G':<10}"
        if storage:
            result += f"{storage_read['value']:<12}{storage_write['value']:<12}"
        if network:
            result += f"{network_read['value']:<12}{network_write['value']:<12}"

        click.secho(result, fg="yellow")
