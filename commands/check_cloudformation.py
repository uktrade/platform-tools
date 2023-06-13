#!/usr/bin/env python

import click


from commands.cloudformation_checks.lint import lint


@click.group()
def copilot():
    pass


def valid_checks():
    # If you add something here, you need to remember to update the valid check docstring in check_cloudformation()
    return {
        "lint": lint,
    }


@copilot.command()
@click.argument("checks", nargs=-1)
def check_cloudformation(checks):
    """Runs the specific CHECK.

    Valid checks are: all and lint
    """

    if len(checks) == 0:
        checks = valid_checks()
        running_checks = "all"
    else:
        running_checks = ' & '.join(', '.join(checks).rsplit(', ', 1))

    if not set(checks) & set(valid_checks()):
        raise ValueError(f"""Invalid check requested in "{running_checks}" """)

    check_single_or_plural = f"""check{"s" if ("all" in checks or len(checks) > 1) else ""}"""

    click.echo(f"""\n>>> Running {running_checks} {check_single_or_plural}\n""")

    for check_name, check_method in valid_checks().items():
        if (check_name in checks):
            click.echo(f"{check_method()}\n")
