import click
from schema import SchemaError

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.domain.config_validator import ConfigValidator
from dbt_platform_helper.domain.copilot_environment import CopilotEnvironment
from dbt_platform_helper.domain.maintenance_page import MaintenancePage
from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.vpc import VpcProvider
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
        MaintenancePage().activate(app, env, svc, template, vpc)
    except PlatformException as err:
        click.secho(str(err), fg="red")
        raise click.Abort


@environment.command()
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
def online(app, env):
    """Remove a maintenance page from an environment."""
    try:
        MaintenancePage().deactivate(app, env)
    except PlatformException as err:
        click.secho(str(err), fg="red")
        raise click.Abort


@environment.command()
@click.option("--name", "-n", required=True)
def generate(name):
    try:
        config_provider = ConfigProvider(ConfigValidator())
        vpc_provider = VpcProvider(get_aws_session_or_abort())
        # TODO - setup loadbalancer provider here too...
        CopilotEnvironment(config_provider, vpc_provider).generate(name)
    # TODO this exception will never be caught as the config provider catches schema errors and aborts
    except SchemaError as ex:
        click.secho(f"Invalid `{PLATFORM_CONFIG_FILE}` file: {str(ex)}", fg="red")
        raise click.Abort
    except PlatformException as err:
        click.secho(str(err), fg="red")
        raise click.Abort


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
        click.secho(str(err), fg="red")
        raise click.Abort
