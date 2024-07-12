import subprocess
from typing import List

import click

from dbt_platform_helper.commands.conduit import add_stack_delete_policy_to_task_role
from dbt_platform_helper.commands.conduit import addon_client_is_running
from dbt_platform_helper.commands.conduit import connect_to_addon_client_task
from dbt_platform_helper.commands.conduit import get_cluster_arn
from dbt_platform_helper.commands.conduit import normalise_secret_name
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.aws import update_postgres_parameter_with_master_secret
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)


@click.group(chain=True, cls=ClickDocOptGroup)
def database():
    check_platform_helper_version_needs_update()


@database.command(name="copy")
@click.argument("source_db", type=str, required=True)
@click.argument("target_db", type=str, required=True)
def copy(source_db: str, target_db: str):
    """Copy source database to target database."""
    app = None
    source_env = None
    target_env = None

    for tag in get_database_tags(source_db):
        if tag["Key"] == "copilot-application":
            app = tag["Value"]
        if tag["Key"] == "copilot-environment":
            source_env = tag["Value"]
            if app is not None:
                break

    for tag in get_database_tags(target_db):
        if tag["Key"] == "copilot-environment":
            target_env = tag["Value"]
            break

    if not app or not source_env or not target_env:
        click.secho(f"""Required database tags not found.""", fg="red")
        exit(1)

    if target_env == "prod":
        click.secho(f"""The target database cannot be a production database.""", fg="red")
        exit(1)

    if source_db == target_db:
        click.secho(f"""Source and target databases are the same.""", fg="red")
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

    click.echo(f"""Starting task to copy data from {source_db} to {target_db}""")

    source_db_connection = get_connection_string(app, source_env, source_db)
    target_db_connection = get_connection_string(app, target_env, target_db)

    application = load_application(app)
    cluster_arn = get_cluster_arn(application, source_env)
    task_name = f"database-copy-{app}-{source_env}-{app}-{target_env}"

    if not addon_client_is_running(application, source_env, cluster_arn, task_name):
        subprocess.call(
            f"copilot task run --app {app} --env {source_env} "
            f"--task-group-name {task_name} "
            f"--image public.ecr.aws/uktrade/tunnel:database-copy "
            f"--env-vars SOURCE_DB_CONNECTION='{source_db_connection}',TARGET_DB_CONNECTION='{target_db_connection}' "
            "--platform-os linux "
            "--platform-arch arm64",
            shell=True,
        )
        add_stack_delete_policy_to_task_role(application, source_env, task_name)
    connect_to_addon_client_task(application, source_env, cluster_arn, task_name)


def get_database_tags(db_identifier: str) -> List[dict]:
    session = get_aws_session_or_abort()
    rds = session.client("rds")

    try:
        db_instance = rds.describe_db_instances(DBInstanceIdentifier=db_identifier)["DBInstances"][
            0
        ]

        return db_instance["TagList"]
    except rds.exceptions.DBInstanceNotFoundFault:
        click.secho(
            f"""Database {db_identifier} not found. Check the database identifier.""", fg="red"
        )
        exit(1)


def get_connection_string(app: str, env: str, db_identifier: str) -> str:
    session = get_aws_session_or_abort()
    addon_name = normalise_secret_name(db_identifier.split(f"{app}-{env}-", 1)[1])
    connection_string_parameter = f"/copilot/{app}/{env}/secrets/{addon_name}_READ_ONLY_USER"
    master_secret_name = f"/copilot/{app}/{env}/secrets/{addon_name}_RDS_MASTER_ARN"
    master_secret_arn = session.client("ssm").get_parameter(
        Name=master_secret_name, WithDecryption=True
    )["Parameter"]["Value"]

    conn = update_postgres_parameter_with_master_secret(
        session, connection_string_parameter, master_secret_arn
    )

    return f"postgres://{conn['username']}:{conn['password']}@{conn['host']}:{conn['port']}/{conn['dbname']}"
