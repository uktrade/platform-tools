import click
from schema import SchemaError

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.domain.config_validator import ConfigValidator
from dbt_platform_helper.domain.copilot_environment import CopilotEnvironment
from dbt_platform_helper.domain.maintenance_page import MaintenancePageProvider
from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
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
        MaintenancePageProvider().activate(app, env, svc, template, vpc)
    except PlatformException as err:
        click.secho(str(err), fg="red")
        raise click.Abort


@environment.command()
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
def online(app, env):
    """Remove a maintenance page from an environment."""
    try:
        MaintenancePageProvider().deactivate(app, env)
    except PlatformException as err:
        click.secho(str(err), fg="red")
        raise click.Abort


@environment.command()
@click.option("--vpc-name", hidden=True)
@click.option("--name", "-n", required=True)
def generate(name, vpc_name):
    if vpc_name:
        click.secho(
            f"This option is deprecated. Please add the VPC name for your envs to {PLATFORM_CONFIG_FILE}",
            fg="red",
        )
        raise click.Abort
    try:
        config_provider = ConfigProvider(ConfigValidator())
        CopilotEnvironment(config_provider).generate(name)
    except SchemaError as ex:
        click.secho(f"Invalid `{PLATFORM_CONFIG_FILE}` file: {str(ex)}", fg="red")
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
    config_provider = ConfigProvider(ConfigValidator())
    TerraformEnvironment(config_provider).generate(name, terraform_platform_modules_version)
