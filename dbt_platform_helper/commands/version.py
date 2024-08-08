import click

from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)


@click.group(chain=True, cls=ClickDocOptGroup)
def version():
    check_platform_helper_version_needs_update()


@version.command()
# @click.argument("source_environment")
# @click.argument("target_environment")
# @click.option("--project-profile", required=True, help="AWS account profile name")
def required(project_profile, source_environment, target_environment):
    pass
