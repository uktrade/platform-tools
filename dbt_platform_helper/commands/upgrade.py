import subprocess

import click

from dbt_platform_helper.providers.io import ClickIOProvider


@click.command()
def upgrade():
    """Update platform-helper to the latest version."""
    try:
        subprocess.run(["pip", "install", "--upgrade", "dbt-platform-helper"])
    except Exception as err:
        ClickIOProvider().abort_with_error(str(err))
