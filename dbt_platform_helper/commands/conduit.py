import click

from dbt_platform_helper.constants import CONDUIT_ADDON_TYPES
from dbt_platform_helper.domain.conduit import Conduit
from dbt_platform_helper.exceptions import AddonNotFoundError
from dbt_platform_helper.exceptions import CreateTaskTimeoutError
from dbt_platform_helper.exceptions import InvalidAddonTypeError
from dbt_platform_helper.exceptions import NoClusterError
from dbt_platform_helper.exceptions import ParameterNotFoundError
from dbt_platform_helper.providers.secrets import SecretNotFoundError
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.click import ClickDocOptCommand
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)

CONDUIT_ACCESS_OPTIONS = ["read", "write", "admin"]


@click.command(cls=ClickDocOptCommand)
@click.argument("addon_name", type=str, required=True)
@click.option("--app", help="Application name", required=True)
@click.option("--env", help="Service environment name", required=True)
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
    except NoClusterError:
        click.secho(f"""No ECS cluster found for "{app}" in "{env}" environment.""", fg="red")
        exit(1)
    except SecretNotFoundError as err:
        click.secho(
            f"""No secret called "{err}" for "{app}" in "{env}" environment.""",
            fg="red",
        )
        exit(1)
    except CreateTaskTimeoutError:
        click.secho(
            f"""Client ({addon_name}) ECS task has failed to start for "{app}" in "{env}" environment.""",
            fg="red",
        )
        exit(1)
    except ParameterNotFoundError:
        click.secho(
            f"""No parameter called "/copilot/applications/{app}/environments/{env}/addons". Try deploying the "{app}" "{env}" environment.""",
            fg="red",
        )
        exit(1)
    except AddonNotFoundError:
        click.secho(
            f"""Addon "{addon_name}" does not exist.""",
            fg="red",
        )
        exit(1)
    except InvalidAddonTypeError as err:
        click.secho(
            f"""Addon type "{err.addon_type}" is not supported, we support: {", ".join(CONDUIT_ADDON_TYPES)}.""",
            fg="red",
        )
        exit(1)
