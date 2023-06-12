#!/usr/bin/env python

from pathlib import Path

import click

BASE_DIR = Path(__file__).parent.parent


@click.group()
def copilot():
    pass


@copilot.command()
@click.argument("check", type=str)
def check_cloudformation(check):
    """Runs the specific CHECK.

    Valid checks are: all and lint
    """

    valid_checks = ["all", "lint"]

    if not valid_checks.__contains__(check):
        raise ValueError(f"Invalid value ({check}) for 'CHECK'")

    click.echo(f"\n>>> Running checks: {check}\n")
