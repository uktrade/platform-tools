import click

from dbt_platform_helper.domain.conduit import Conduit
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.cloudformation import CloudFormation
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.secrets import Secrets
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.click import ClickDocOptCommand

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
    PlatformHelperVersioning().check_if_needs_update()
    application = load_application(app)

    try:
        secrets_provider: Secrets = Secrets(
            application.environments[env].session.client("ssm"),
            application.environments[env].session.client("secretsmanager"),
            application.name,
            env,
        )
        cloudformation_provider: CloudFormation = CloudFormation(
            application.environments[env].session.client("cloudformation"),
            application.environments[env].session.client("iam"),
            application.environments[env].session.client("ssm"),
        )

        ecs_provider: ECS = ECS(
            application.environments[env].session.client("ecs"),
            application.environments[env].session.client("ssm"),
            application.name,
            env,
        )

        Conduit(application, secrets_provider, cloudformation_provider, ecs_provider).start(
            env, addon_name, access
        )
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
