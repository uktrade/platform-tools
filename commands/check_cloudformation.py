#!/usr/bin/env python

import click

@click.group()
def copilot():
    pass


def valid_checks():
    return ["all", "lint"]


@copilot.command()
@click.argument("check", type=str)
def check_cloudformation(check):
    """Runs the specific CHECK.

    Valid checks are: all and lint
    """

    if not check in valid_checks():
        raise ValueError(f"Invalid value ({check}) for 'CHECK'")

    click.echo(f"\n>>> Running checks: {check}\n")

    # Call the method
