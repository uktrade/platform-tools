import click

from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.platform_config import get_environment_pipeline_names
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)
from dbt_platform_helper.utils.versioning import get_desired_platform_helper_version


@click.group(chain=True, cls=ClickDocOptGroup)
def version():
    check_platform_helper_version_needs_update()


@version.command(help="Print the version of platform-tools desired by the current project")
@click.option(
    "--pipeline",
    required=False,
    type=click.Choice(get_environment_pipeline_names()),
    help="Take into account platform-tools version overrides in the specified pipeline",
)
def print_desired(pipeline):
    desired_version = get_desired_platform_helper_version(pipeline)
    click.secho(desired_version)
