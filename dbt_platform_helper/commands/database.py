import click

from dbt_platform_helper.commands.environment import AVAILABLE_TEMPLATES
from dbt_platform_helper.domain.database_copy import DatabaseCopy
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
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
    help="The environment you are dumping data from",
)
@click.option(
    "--database", type=str, required=True, help="The name of the database you are dumping data from"
)
@click.option(
    "--from-vpc",
    type=str,
    help="The vpc the specified environment is running in. Required unless you are running the command from your deploy repo",
)
@click.option(
    "--filename",
    type=str,
    help="Specify a name for the database dump file. Recommended if the same dump database is being used for multiple load environments",
)
def dump(app, from_env, database, from_vpc, filename):
    """Dump a database into an S3 bucket."""
    try:
        data_copy = DatabaseCopy(app, database)
        data_copy.dump(from_env, from_vpc, filename)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))


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
@click.option(
    "--filename",
    type=str,
    help="Specify a name for the database dump file. Recommended if the same dump database is being used for multiple load environments",
)
def load(app, to_env, database, to_vpc, auto_approve, filename):
    """Load a database from an S3 bucket."""
    try:
        data_copy = DatabaseCopy(app, database, auto_approve)
        data_copy.load(to_env, to_vpc, filename)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))


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
@click.option("--svc", type=str, required=True, multiple=True, default=["web"])
@click.option(
    "--template",
    type=click.Choice(AVAILABLE_TEMPLATES),
    default="default",
    help="The maintenance page you wish to put up.",
)
@click.option("--no-maintenance-page", flag_value=True)
def copy(
    app,
    from_env,
    to_env,
    database,
    from_vpc,
    to_vpc,
    auto_approve,
    svc,
    template,
    no_maintenance_page,
):
    """Copy a database between environments."""
    try:
        data_copy = DatabaseCopy(app, database, auto_approve)
        data_copy.copy(from_env, to_env, from_vpc, to_vpc, svc, template, no_maintenance_page)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
