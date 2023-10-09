#!/usr/bin/env python

from importlib.metadata import version

import click

from dbt_copilot_helper.commands.bootstrap import bootstrap as bootstrap_commands
from dbt_copilot_helper.commands.check_cloudformation import (
    check_cloudformation as check_cloudformation_command,
)
from dbt_copilot_helper.commands.codebuild import codebuild as codebuild_commands
from dbt_copilot_helper.commands.conduit import conduit as conduit_commands
from dbt_copilot_helper.commands.config import config as config_commands
from dbt_copilot_helper.commands.copilot import copilot as copilot_commands
from dbt_copilot_helper.commands.dns import domain as domain_commands
from dbt_copilot_helper.commands.svc import svc as svc_commands
from dbt_copilot_helper.commands.waf import waf as waf_commands
from dbt_copilot_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup)
@click.version_option(
    version=version("dbt-copilot-tools"),
    message=f"dbt-copilot-tools %(version)s",
)
def copilot_helper():
    pass


copilot_helper.add_command(bootstrap_commands)
copilot_helper.add_command(check_cloudformation_command)
copilot_helper.add_command(codebuild_commands)
copilot_helper.add_command(conduit_commands)
copilot_helper.add_command(config_commands)
copilot_helper.add_command(copilot_commands)
copilot_helper.add_command(domain_commands)
copilot_helper.add_command(svc_commands)
copilot_helper.add_command(waf_commands)

if __name__ == "__main__":
    copilot_helper()
