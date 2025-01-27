import click

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.domain.config_validator import ConfigValidator
from dbt_platform_helper.domain.copilot_environment import CopilotEnvironment
from dbt_platform_helper.domain.maintenance_page import MaintenancePage
from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.cloudformation import CloudFormation
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.vpc import VpcProvider
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)

AVAILABLE_TEMPLATES = ["default", "migration", "dmas-migration"]


@click.group(cls=ClickDocOptGroup)
def environment():
    """Commands affecting environments."""
    check_platform_helper_version_needs_update()


@environment.command()
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
@click.option("--svc", type=str, required=True, multiple=True, default=["web"])
@click.option(
    "--template",
    type=click.Choice(AVAILABLE_TEMPLATES),
    default="default",
    help="The maintenance page you wish to put up.",
)
@click.option("--vpc", type=str)
def offline(app, env, svc, template, vpc):
    """Take load-balanced web services offline with a maintenance page."""

    try:
        application = load_application(app)
        MaintenancePage(application).activate(env, svc, template, vpc)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))


@environment.command()
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
def online(app, env):
    """Remove a maintenance page from an environment."""

    try:
        application = load_application(app)
        MaintenancePage(application).deactivate(env)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))


@environment.command()
@click.option(
    "--name",
    "-n",
    required=True,
    help="The name of the environment to generate a copilot manifest for.",
)
def generate(name):
    """Gathers various IDs and ARNs from AWS and generates the AWS Copilot
    environment manifest at copilot/environments/<environment>/manifest.yml."""

    click_io = ClickIOProvider()
    try:
        session = get_aws_session_or_abort()
        config_provider = ConfigProvider(ConfigValidator())
        vpc_provider = VpcProvider(session)
        cloudformation_provider = CloudFormation(session.client("cloudformation"))

        CopilotEnvironment(
            config_provider, vpc_provider, cloudformation_provider, session
        ).generate(name)
    except PlatformException as err:
        click_io.abort_with_error(str(err))


@environment.command(help="Generate terraform manifest for the specified environment.")
@click.option(
    "--name", "-n", required=True, help="The name of the environment to generate a manifest for."
)
@click.option(
    "--terraform-platform-modules-version",
    help=f"Override the default version of terraform-platform-modules. (Default version is '{DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION}').",
)
def generate_terraform(name, terraform_platform_modules_version):

    try:
        config_provider = ConfigProvider(ConfigValidator())
        TerraformEnvironment(config_provider).generate(name, terraform_platform_modules_version)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
