import click

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.versioning import RequiredVersion


@click.command(help="Print the version of platform-tools required by the current project")
@click.option(
    "--pipeline",
    required=False,
    type=str,
    help="Take into account platform-tools version overrides in the specified pipeline",
)
def version(pipeline):
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
    try:
        RequiredVersion().get_required_version(pipeline)
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
