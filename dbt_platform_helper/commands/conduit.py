import click

from dbt_platform_helper.domain.conduit import Conduit
from dbt_platform_helper.providers.aws import SecretNotFoundError
from dbt_platform_helper.providers.copilot import CONDUIT_ACCESS_OPTIONS
from dbt_platform_helper.providers.copilot import CONDUIT_ADDON_TYPES
from dbt_platform_helper.providers.copilot import AddonNotFoundError
from dbt_platform_helper.providers.copilot import CreateTaskTimeoutError
from dbt_platform_helper.providers.copilot import InvalidAddonTypeError
from dbt_platform_helper.providers.copilot import NoClusterError
from dbt_platform_helper.providers.copilot import ParameterNotFoundError
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.click import ClickDocOptCommand
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)


@click.command(cls=ClickDocOptCommand)
@click.argument("addon_name", type=str, required=True)
@click.option("--app", help="AWS application name", required=True)
@click.option("--env", help="AWS environment name", required=True)
@click.option(
    "--access",
    default="read",
    type=click.Choice(CONDUIT_ACCESS_OPTIONS),
    help="Allow write or admin access to database addons",
)
def conduit(addon_name: str, app: str, env: str, access: str):
    """Create a conduit connection to an addon."""
    check_platform_helper_version_needs_update()
    application = load_application(app)

    try:
        Conduit(env, application).start(env, addon_name, access)
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
