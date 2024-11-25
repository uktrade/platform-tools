import click

from dbt_platform_helper.domain.conduit import Conduit
from dbt_platform_helper.exceptions import AWSException
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.click import ClickDocOptCommand
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)

CONDUIT_ACCESS_OPTIONS = ["read", "write", "admin"]


@click.command(cls=ClickDocOptCommand)
@click.argument("addon_name", type=str, required=True)
@click.option("--app", help="Application name", required=True)
@click.option("--env", help="Environment name", required=True)
@click.option(
    "--access",
    default="read",
    type=click.Choice(CONDUIT_ACCESS_OPTIONS),
    help="Allow read, write or admin access to the database addons.",
)
def conduit(addon_name: str, app: str, env: str, access: str):
    """Opens a shell for a given addon_name create a conduit connection to
    interact with postgres, opensearch or redis."""
    check_platform_helper_version_needs_update()
    application = load_application(app)

    try:
        Conduit(application).start(env, addon_name, access)
    except AWSException as err:
        click.secho(str(err), fg="red")
        exit(1)
