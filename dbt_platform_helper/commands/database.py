import json
import subprocess

import click
from boto3 import Session

from dbt_platform_helper.commands.conduit import addon_client_is_running
from dbt_platform_helper.commands.conduit import get_cluster_arn
from dbt_platform_helper.commands.conduit import normalise_secret_name
from dbt_platform_helper.commands.conduit import update_parameter_with_secret
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)


@click.group(chain=True, cls=ClickDocOptGroup)
def database():
    check_platform_helper_version_needs_update()


@database.command(name="copy")
@click.option("--source-db", help="Source database identifier", required=True)
@click.option("--target-db", help="Target database identifier", required=True)
def copy(source_db: str, target_db: str):
    """Copy source database to target database."""

    session = get_aws_session_or_abort()
    rds = session.client("rds")

    try:
        source_db_instance = rds.describe_db_instances(DBInstanceIdentifier=source_db)[
            "DBInstances"
        ][0]
    except rds.exceptions.DBInstanceNotFoundFault:
        click.secho(
            f"""Source db {source_db} not found. Check the database identifier.""", fg="red"
        )
        exit(1)
    try:
        target_db_instance = rds.describe_db_instances(DBInstanceIdentifier=target_db)[
            "DBInstances"
        ][0]
    except rds.exceptions.DBInstanceNotFoundFault:
        click.secho(
            f"""Target db {target_db} not found. Check the database identifier.""", fg="red"
        )
        exit(1)

    # Check account
    # sts = session.client("sts")
    # account = sts.get_caller_identity()
    # print(account)

    app = None
    source_env = None
    target_env = None

    for tag in source_db_instance["TagList"]:
        if tag["Key"] == "copilot-application":
            app = tag["Value"]
        if tag["Key"] == "copilot-environment":
            source_env = tag["Value"]

    for tag in target_db_instance["TagList"]:
        if tag["Key"] == "copilot-environment":
            target_env = tag["Value"]

    if not app and source_env and target_env:
        click.secho(f"""Required tags not found.""", fg="red")
        exit(1)

    if target_env == "prod":
        click.secho(f"""The --target-db option cannot be a production database.""", fg="red")
        exit(1)

    if not click.confirm(
        click.style("Copying data from ", fg="yellow")
        + click.style(f"{source_db} ", fg="white", bold=True)
        + click.style(f"in environment {source_env} to ", fg="yellow", bold=True)
        + click.style(f"{target_db} ", fg="white", bold=True)
        + click.style(f"in environment {target_env}\n", fg="yellow", bold=True)
        + click.style("Do you want to continue?", fg="yellow"),
    ):
        exit()

    click.echo(f"""Copying data from {source_db} to {target_db}""")

    source_db_connection = _get_connection_string(session, app, source_env, source_db)
    target_db_connection = _get_connection_string(session, app, target_env, target_db)

    application = load_application(app)
    cluster_arn = get_cluster_arn(application, source_env)
    task_name = f"database-copy-{app}-{source_env}-{app}-{target_env}"

    if not addon_client_is_running(application, source_env, cluster_arn, task_name):
        subprocess.call(
            f"copilot task run --app {app} --env {source_env} " f"--task-group-name {task_name} "
            # f"--image public.ecr.aws/uktrade/tunnel:database-copy "
            f"--dockerfile images/tools/database-copy/Dockerfile "
            f'--env-vars SOURCE_DB_CONNECTION="{json.dumps(source_db_connection)}",TARGET_DB_CONNECTION="{json.dumps(target_db_connection)}" '
            "--platform-os linux "
            "--platform-arch arm64",
            shell=True,
        )

        # Might need these to cleanup the cloudformation stack
        # add_stack_delete_policy_to_task_role(application, env, task_name)
        # update_conduit_stack_resources(
        #     application, env, addon_type, addon_name, task_name, parameter_name
        # )

    # connect_to_addon_client_task(application, source_env, cluster_arn, task_name)


def _get_connection_string(session: Session, app: str, env: str, db_identifier: str) -> str:
    addon_name = normalise_secret_name(db_identifier.split(f"{app}-{env}-", 1)[1])
    connection_string_parameter = f"/copilot/{app}/{env}/secrets/{addon_name}_READ_ONLY_USER"
    master_secret_name = f"/copilot/{app}/{env}/secrets/{addon_name}_RDS_MASTER_ARN"
    master_secret_arn = session.client("ssm").get_parameter(
        Name=master_secret_name, WithDecryption=True
    )["Parameter"]["Value"]

    connection_string = update_parameter_with_secret(
        session, connection_string_parameter, master_secret_arn
    )

    return connection_string
