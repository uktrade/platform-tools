#!/usr/bin/env python

from importlib.metadata import version

import click

from dbt_platform_helper.commands.application import application as application_commands
from dbt_platform_helper.commands.codebase import codebase as codebase_commands
from dbt_platform_helper.commands.conduit import conduit as conduit_commands
from dbt_platform_helper.commands.config import config as config_commands
from dbt_platform_helper.commands.copilot import copilot as copilot_commands
from dbt_platform_helper.commands.database import database as database_commands
from dbt_platform_helper.commands.environment import environment as environment_commands
from dbt_platform_helper.commands.generate import generate as generate_commands
from dbt_platform_helper.commands.notify import notify as notify_commands
from dbt_platform_helper.commands.pipeline import pipeline as pipeline_commands
from dbt_platform_helper.commands.secrets import secrets as secrets_commands
from dbt_platform_helper.commands.version import version as version_commands
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup)
@click.version_option(
    version=version("dbt-platform-helper"),
    message=f"dbt-platform-helper %(version)s",
)
def platform_helper():
    pass


platform_helper.add_command(application_commands)
platform_helper.add_command(codebase_commands)
platform_helper.add_command(conduit_commands)
platform_helper.add_command(config_commands)
platform_helper.add_command(copilot_commands)
platform_helper.add_command(environment_commands)
platform_helper.add_command(generate_commands)
platform_helper.add_command(pipeline_commands)
platform_helper.add_command(secrets_commands)
platform_helper.add_command(notify_commands)
platform_helper.add_command(database_commands)
platform_helper.add_command(version_commands)

if __name__ == "__main__":
    platform_helper(auto_envvar_prefix="DBT_PLATFORM")
