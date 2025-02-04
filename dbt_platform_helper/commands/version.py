import click

from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.versioning import get_required_platform_helper_version


@click.group(chain=True, cls=ClickDocOptGroup)
def version():
    """Contains subcommands for getting version information about the current
    project."""
    get_platform_helper_for_project()


def get_platform_helper_for_project():
    pipeline = None
    required_version = get_required_platform_helper_version(pipeline)
    click.secho(required_version)
