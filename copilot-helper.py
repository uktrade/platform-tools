#!/usr/bin/env python

import click

from commands.bootstrap_cli import bootstrap as bootstrap_commands
from commands.codebuild_cli import codebuild as codebuild_commands
from commands.copilot_cli import copilot as copilot_commands
from commands.dns_cli import domain as domain_commands


@click.group()
def cli():
    pass


cli.add_command(bootstrap_commands)
cli.add_command(copilot_commands)
cli.add_command(codebuild_commands)
cli.add_command(domain_commands)


if __name__ == "__main__":
    cli()
