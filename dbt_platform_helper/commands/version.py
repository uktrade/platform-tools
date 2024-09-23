import click

from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.platform_config import get_environment_pipeline_names
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)
from dbt_platform_helper.utils.versioning import get_required_platform_helper_version


@click.group(chain=True, cls=ClickDocOptGroup)
def version():
    """Contains subcommands for getting version information about the current
    project."""
    check_platform_helper_version_needs_update()


@version.command(help="Print the version of platform-tools required by the current project")
@click.option(
    "--pipeline",
    required=False,
    type=click.Choice(get_environment_pipeline_names()),
    help="Take into account platform-tools version overrides in the specified pipeline",
)
def get_platform_helper_for_project(pipeline):
    """
    Version precedence is in this order:
        - if the --pipeline option is supplied, the version in 'platform-config.yml' in:
            environment_pipelines:
                <pipeline>:
                    ...
                    versions:
                        platform-helper
        - The version from default_versions/platform-helper in 'platform-config.yml'
        - Fall back on the version in the deprecated '.platform-helper-version' file
    """
    required_version = get_required_platform_helper_version(pipeline)
    click.secho(required_version)
