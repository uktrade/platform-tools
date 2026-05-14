import click

from dbt_platform_helper.domain.job import JobManager
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.parameter_store import ParameterStore
from dbt_platform_helper.providers.service import ServiceRepository
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
@click.option(
    "--follow",
    "-f",
    help="Wait for the execution to finish and report it's final status",
    is_flag=True,
)
def run(app: str, env: str, name: str, follow: bool):
    """Runs a scheduled job on demand."""

    try:
        application = load_application(app=app, env=env)

        try:
            sfn_client = application.environments[env].session.client("stepfunctions")
            account_id = application.environments[env].account_id
        except KeyError:
            raise ApplicationEnvironmentNotFoundException(app, env)

        job_runner: StepFunctions = StepFunctions(sfn_client, application.name, env, account_id)

        JobManager(job_runner=job_runner).start_execution(app, env, name, follow)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))


@job.command()
@click.option("--app", "-a", help="Application name", required=True)
@click.option("--env", "-e", help="Environment name", required=True)
def ls(app: str, env: str):
    """Lists deployed scheduled jobs."""
    io = ClickIOProvider()

    try:
        application = load_application(app=app, env=env)

        try:
            ssm_client = application.environments[env].session.client("ssm")
            account_id = application.environments[env].account_id
        except KeyError:
            raise ApplicationEnvironmentNotFoundException(app, env)

        service_repository = ServiceRepository(ParameterStore(ssm_client, True))

        JobManager(job_runner=None, service_repository=service_repository, io=io).list_jobs(
            app, env
        )

    except PlatformException as err:
        io.abort_with_error(str(err))
