import click

from dbt_platform_helper.commands.database_helpers import DatabaseCopy
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(chain=True, cls=ClickDocOptGroup)
def database():
    pass


@database.command(name="dump")
@click.option("--account-id", type=str, required=True)
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
@click.option("--database", type=str, required=True)
@click.option("--vpc-name", type=str, required=True)
def dump(account_id, app, env, database, vpc_name):
    """Dump a database into an S3 bucket."""
    data_copy = DatabaseCopy(account_id, app, env, database, vpc_name)
    data_copy.dump()


@database.command(name="load")
@click.option("--account-id", type=str, required=True)
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
@click.option("--database", type=str, required=True)
@click.option("--vpc-name", type=str, required=True)
def load(account_id, app, env, database, vpc_name):
    """Load a database from an S3 bucket."""
    data_copy = DatabaseCopy(account_id, app, env, database, vpc_name)
    data_copy.load()
