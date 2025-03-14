#!/usr/bin/env python

# application commands are deprecated, do not spend time refactoring them
# Service teams are trained to use them as a replacement for cf app(s)

import time
from datetime import datetime
from datetime import timedelta

import click
from prettytable import PrettyTable

from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.click import ClickDocOptGroup

YELLOW = "\033[93m"
CYAN = "\033[96m"


def get_query_results(env, app, query_string, timeout):
    label_text = click.style("Waiting for results:", fg="yellow")
    fill_char = click.style("#", fg="yellow")
    empty_char = click.style("-", fg="yellow", dim=True)

    application = load_application(app)
    project_session = application.environments[env].session

    click.secho(
        f"Showing status for app {app}",
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

    elapsed = 0
    # Need to wait a few seconds for the query to be available, up to timeout value.
    with click.progressbar(
        label=label_text,
        length=timeout,
        show_eta=False,
        show_percent=False,
        fill_char=fill_char,
        empty_char=empty_char,
    ) as progress_bar:
        while (
            len(logs_client.get_query_results(queryId=cpu_response_id["queryId"])["results"]) == 0
            and elapsed < timeout
        ):
            time.sleep(1)
            progress_bar.update(1)
            elapsed = elapsed + 1

    if elapsed == timeout:
        click.secho(
            f"Timeout threshold breached, no results returned in {timeout} seconds.\nExiting...",
            fg="red",
        )
        exit()

    cpu_response = logs_client.get_query_results(queryId=cpu_response_id["queryId"])

    return cpu_response


@click.group(chain=True, cls=ClickDocOptGroup, deprecated=True)
def application():
    """[DEPRECATED] Application metrics."""
    PlatformHelperVersioning().check_if_needs_update()


@application.command(deprecated=True)
@click.option("--env", type=str, required=True)
@click.option("--app", type=str, required=True)
@click.option("--storage", is_flag=True)
@click.option("--network", is_flag=True)
def container_stats(env, app, storage, network):
    """[DEPRECATED] Command to get application container level metrics."""

    # Query string to get the required container stats
    query_string = "stats max(CpuUtilized), max(MemoryUtilized) by TaskId, ContainerName, TaskDefinitionFamily, TaskDefinitionRevision, Image, StorageReadBytes, StorageWriteBytes, NetworkRxPackets, NetworkTxBytes | filter Type='Container' | sort TaskId, ContainerName desc"
    cpu_response = get_query_results(env, app, query_string, 15)

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
        cpu = f"{float(field[9]['value']):.1f}%"
        memory = f"{field[10]['value']}M"

        # Nothing to compare to at start.
        if index > 0:
            end_index = index - 1
        else:
            end_index = 0

        # If its a new task then create new table and display the headings.
        if (
            index == 0
            or cpu_response["results"][index][0]["value"]
            != cpu_response["results"][end_index][0]["value"]
        ):
            result_table = PrettyTable()
            click.echo(
                click.style(f"\n{'Type:':<10}", fg="green")
                + click.style(f"{cont_name_short}", fg="green", bold=True)
            )

            click.echo(
                click.style(f"{'Task ID:':<10}", fg="green")
                + click.style(f"{task}", fg="green", bold=True)
                + "\n"
            )

            heading_fields = [
                f"{CYAN}Container Name",
                f"{CYAN}CPU",
                f"{CYAN}Memory",
                f"{CYAN}Revision",
            ]

            # Optional parameters.
            if storage:
                heading_fields.append(f"{CYAN}Disk Read")
                heading_fields.append(f"{CYAN}Disk Write")
            if network:
                heading_fields.append(f"{CYAN}Net Read")
                heading_fields.append(f"{CYAN}Net Write")

            heading_fields.append(f"{CYAN}Image")

            result_table.field_names = heading_fields
            for item in heading_fields:
                result_table.align[f"{item}"] = "l"
            result_table.border = False

        # Print container stats
        values = [
            f"{YELLOW}{cont_name}",
            f"{YELLOW}{cpu}",
            f"{YELLOW}{memory}",
            f"{YELLOW}{task_def_revision}",
        ]

        # Optional stats.
        if storage:
            values.append(f"{storage_read}")
            values.append(f"{storage_write}")
        if network:
            values.append(f"{network_read}")
            values.append(f"{network_write}")
        values.append(f"{image}")

        result_table.add_row(values)

        # Print table when new task is next or at end of loop.
        if (
            index == len(cpu_response["results"]) - 1
            or cpu_response["results"][index][0]["value"]
            != cpu_response["results"][index + 1][0]["value"]
        ):
            click.secho(result_table)

        index = index + 1


@application.command(deprecated=True)
@click.option("--env", type=str, required=True)
@click.option("--app", type=str, required=True)
@click.option("--disk", is_flag=True)
@click.option("--storage", is_flag=True)
@click.option("--network", is_flag=True)
def task_stats(env, app, disk, storage, network):
    """[DEPRECATED] Command to get application task level metrics."""

    # Query string to get the required container stats
    query_string = "stats max(CpuUtilized), max(MemoryUtilized), max(EphemeralStorageUtilized) by TaskId, TaskDefinitionFamily, TaskDefinitionRevision, StorageReadBytes, StorageWriteBytes, NetworkRxPackets, NetworkTxBytes, KnownStatus | filter Type='Task' | sort TaskId desc"
    cpu_response = get_query_results(env, app, query_string, 15)

    click.echo(
        click.style(f"\n{'Name:':<20}", fg="green") + click.style(f"{app}", fg="green", bold=True)
    )

    click.echo(
        click.style(f"{'No of instances:':<20}", fg="green")
        + click.style(len(cpu_response["results"]), fg="green", bold=True)
        + "\n"
    )

    result_table = PrettyTable()
    heading_fields = [
        f"{CYAN}Type",
        f"{CYAN}TaskID",
        f"{CYAN}Revision",
        f"{CYAN}Status",
        f"{CYAN}CPU",
        f"{CYAN}Memory",
    ]

    # Add to heading if additional parameters are used.
    if disk:
        heading_fields.append(f"{CYAN}Disk")
    if storage:
        heading_fields.append(f"{CYAN}Disk Read")
        heading_fields.append(f"{CYAN}Disk Write")
    if network:
        heading_fields.append(f"{CYAN}Net Read")
        heading_fields.append(f"{CYAN}Net Write")

    result_table.field_names = heading_fields

    for item in heading_fields:
        result_table.align[f"{item}"] = "l"

    result_table.border = False

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
        values = [
            f"{YELLOW}{taskdef['value'].split('-')[-1]}",
            f"{YELLOW}{task['value']}",
            f"{YELLOW}{task_def_revision['value']}",
            f"{YELLOW}{status['value']}",
            f"{YELLOW}{'%.1f' % float(cpu['value']) + '%'}",
            f"{YELLOW}{memory['value'] + 'M'}",
        ]

        # Optional stats.
        if disk:
            values.append(f"{dsk['value'] + 'G'}")
        if storage:
            values.append(f"{storage_read['value']}")
            values.append(f"{storage_write['value']}")
        if network:
            values.append(f"{network_read['value']}")
            values.append(f"{network_write['value']}")

        result_table.add_row(values)

    click.secho(result_table)
