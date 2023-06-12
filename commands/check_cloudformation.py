#!/usr/bin/env python

import click


from commands.cloudformation_checks.lint import lint


@click.group()
def copilot():
    pass


def valid_checks():
    return {
        "all": lambda: None,
        "lint": lint,
    }


@copilot.command()
@click.argument("check", type=str)
def check_cloudformation(check):
    """Runs the specific CHECK.

    Valid checks are: all and lint
    """

    if not check in valid_checks():
        raise ValueError(f"Invalid value ({check}) for 'CHECK'")

    click.echo(f"""\n>>> Running {check} check{"s" if check == "all" else ""}\n""")

    for check_name, check_method in valid_checks().items():
        if check in ["all", check_name] and check_name != "all":
            click.echo(f"{check_method()}\n")
