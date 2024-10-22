import click

from dbt_platform_helper.commands.database_helpers import DatabaseCopy
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(chain=True, cls=ClickDocOptGroup)
def database():
    pass


@database.command(name="dump")
@click.option("--app", type=str)
@click.option("--env", type=str, required=True)
@click.option("--database", type=str, required=True)
@click.option("--vpc-name", type=str, required=True)
def dump(app, env, database, vpc_name):
    """Dump a database into an S3 bucket."""
    data_copy = DatabaseCopy(app, database)
    data_copy.dump(env, vpc_name)


@database.command(name="load")
@click.option("--app", type=str)
@click.option("--env", type=str, required=True)
@click.option("--database", type=str, required=True)
@click.option("--vpc-name", type=str, required=True)
def load(app, env, database, vpc_name):
    """Load a database from an S3 bucket."""
    data_copy = DatabaseCopy(app, database)
    data_copy.load(env, vpc_name)


@database.command(name="copy")
@click.option("--app", type=str)
@click.option("--from", "from_env", type=str, required=True)
@click.option("--to", "to_env", type=str, required=True)
@click.option("--database", type=str, required=True)
@click.option("--from-vpc", type=str, required=True)
@click.option("--to-vpc", type=str, required=True)
def copy(app, from_env, to_env, database, from_vpc, to_vpc):
    """Copy a database from an S3 bucket."""
    data_copy = DatabaseCopy(app, database)
    data_copy.dump(from_env, from_vpc)
    data_copy.load(to_env, to_vpc)
