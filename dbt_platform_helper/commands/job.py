import click

from dbt_platform_helper.domain.job import JobManager
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.step_functions import StepFunctions
from dbt_platform_helper.utils.application import (
    ApplicationEnvironmentNotFoundException,
)
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup)
def job():
    """Commands for managing a scheduled job."""


@job.command()
@click.option("--app", "-a", help="Application name", required=True)
@click.option("--env", "-e", help="Environment name", required=True)
@click.option("--name", "-n", help="Name of the scheduled job", required=True)
@click.option("--follow", is_flag=True)
def run(app: str, env: str, name: str, follow: bool):
    """Runs a scheduled job on demand."""

    try:
        application = load_application(app=app, env=env)

        try:
            sfn_client = application.environments[env].session.client("stepfunctions")
        except KeyError:
            raise ApplicationEnvironmentNotFoundException(app, env)

        sfn_provider: StepFunctions = StepFunctions(
            sfn_client,
            application.name,
            env,
        )

        JobManager(sfn_provider=sfn_provider).run(app, env, name, follow)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
