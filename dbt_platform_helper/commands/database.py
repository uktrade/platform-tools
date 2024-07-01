import click

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

    # Get source and target databases
    session = get_aws_session_or_abort()
    source_db_instance = session.client("rds").describe_db_instances(
        DBInstanceIdentifier=source_db
    )["DBInstances"][0]
    target_db_instance = session.client("rds").describe_db_instances(
        DBInstanceIdentifier=target_db
    )["DBInstances"][0]

    # Get application and environment from source database tags
    application = None
    source_env = None
    target_env = None

    for tag in source_db_instance["TagList"]:
        if tag["Key"] == "copilot-application":
            application = tag["Value"]
        if tag["Key"] == "copilot-environment":
            source_env = tag["Value"]

    for tag in target_db_instance["TagList"]:
        if tag["Key"] == "copilot-environment":
            target_env = tag["Value"]

    if not click.confirm(
        click.style("Copying data from ", fg="yellow")
        + click.style(f"{source_db} ", fg="white", bold=True)
        + click.style(f"in environment {source_env} to ", fg="yellow", bold=True)
        + click.style(f"{target_db} ", fg="white", bold=True)
        + click.style(f"in environment {target_env}\n", fg="yellow", bold=True)
        + click.style("Do you want to continue?", fg="yellow"),
    ):
        exit()

    print(application, source_env, target_env)
