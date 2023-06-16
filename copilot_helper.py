#!/usr/bin/env python

from importlib.metadata import version

import click

from commands.bootstrap_cli import bootstrap as bootstrap_commands
from commands.check_cloudformation import check_cloudformation as check_cloudformation_command
from commands.codebuild_cli import codebuild as codebuild_commands
from commands.copilot_cli import copilot as copilot_commands
from commands.dns_cli import domain as domain_commands


@click.group()
@click.version_option(
    version=version("dbt-copilot-tools"),
    message=f"dbt-copilot-tools %(version)s",
)
def cli():
    pass


cli.add_command(bootstrap_commands)
cli.add_command(check_cloudformation_command)
cli.add_command(copilot_commands)
cli.add_command(codebuild_commands)
cli.add_command(domain_commands)

if __name__ == "__main__":
    cli()
