#!/usr/bin/env python

from importlib.metadata import version

import click

from commands.bootstrap_cli import bootstrap as bootstrap_commands
from commands.check_cloudformation import \
    check_cloudformation as check_cloudformation_command
from commands.codebuild_cli import codebuild as codebuild_commands
from commands.conduit_cli import conduit as conduit_commands
from commands.copilot_cli import copilot as copilot_commands
from commands.dns_cli import domain as domain_commands
from commands.waf_cli import waf as waf_commands


@click.group()
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
copilot_helper.add_command(copilot_commands)
copilot_helper.add_command(domain_commands)
copilot_helper.add_command(waf_commands)

if __name__ == "__main__":
    copilot_helper()
