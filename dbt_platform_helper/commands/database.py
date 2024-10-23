import click

from dbt_platform_helper.commands.database_helpers import DatabaseCopy
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(chain=True, cls=ClickDocOptGroup)
def database():
    """Commands to copy data between databases."""


@database.command(name="dump")
@click.option(
    "--app",
    type=str,
    help="The application name. Required unless you are running the command from your deploy repo",
)
@click.option(
    "--from",
    "from_env",
    type=str,
    required=True,
    help="This is required unless you are running the command from your deploy repo",
)
@click.option(
    "--database", type=str, required=True, help="The name of the database you are dumping data from"
)
@click.option(
    "--from-vpc",
    type=str,
    help="The vpc the specified environment is running in. Required unless you are running the command from your deploy repo",
)
def dump(app, from_env, database, from_vpc):
    """Dump a database into an S3 bucket."""
    data_copy = DatabaseCopy(app, database)
    data_copy.dump(from_env, from_vpc)


@database.command(name="load")
@click.option(
    "--app",
    type=str,
    help="The application name. Required unless you are running the command from your deploy repo",
)
@click.option(
    "--to", "to_env", type=str, required=True, help="The environment you are loading data into"
)
@click.option(
    "--database", type=str, required=True, help="The name of the database you are loading data into"
)
@click.option(
    "--to-vpc",
    type=str,
    help="The vpc the specified environment is running in. Required unless you are running the command from your deploy repo",
)
@click.option("--auto-approve/--no-auto-approve", default=False)
def load(app, to_env, database, to_vpc, auto_approve):
    """Load a database from an S3 bucket."""
    data_copy = DatabaseCopy(app, database, auto_approve)
    data_copy.load(to_env, to_vpc)


@database.command(name="copy")
@click.option(
    "--app",
    type=str,
    help="The application name. Required unless you are running the command from your deploy repo",
)
@click.option(
    "--from", "from_env", type=str, required=True, help="The environment you are copying data from"
)
@click.option(
    "--to", "to_env", type=str, required=True, help="The environment you are copying data into"
)
@click.option(
    "--database", type=str, required=True, help="The name of the database you are copying"
)
@click.option(
    "--from-vpc",
    type=str,
    help="The vpc the environment you are copying from is running in. Required unless you are running the command from your deploy repo",
)
@click.option(
    "--to-vpc",
    type=str,
    help="The vpc the environment you are copying into is running in. Required unless you are running the command from your deploy repo",
)
@click.option("--auto-approve/--no-auto-approve", default=False)
def copy(app, from_env, to_env, database, from_vpc, to_vpc, auto_approve):
    """Copy a database between environments."""
    data_copy = DatabaseCopy(app, database, auto_approve)
    data_copy.dump(from_env, from_vpc)
    data_copy.load(to_env, to_vpc)
