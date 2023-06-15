#!/usr/bin/env python
import os
from pathlib import Path

import click

from commands.bootstrap_cli import make_config
from commands.cloudformation_checks.CheckCloudformationFailure import CheckCloudformationFailure
from commands.cloudformation_checks.lint import lint
from commands.copilot_cli import make_storage

BASE_DIR = Path(__file__).parent.parent


@click.group()
def copilot():
    pass


def valid_checks():
    # If you add something here, you need to remember to update the valid check docstring in check_cloudformation()
    return {
        "lint": lint,
    }


@click.group(invoke_without_command=True)
@click.argument("checks", nargs=-1)
@click.pass_context
def check_cloudformation(ctx, checks):
    """Runs the specific CHECK.

    Valid checks are: all and lint
    """

    if len(checks) == 0:
        checks = valid_checks()
        running_checks = "all"
    else:
        running_checks = ' & '.join(', '.join(checks).rsplit(', ', 1))

    for check in checks:
        if check not in valid_checks():
            click.secho(f"""Invalid check requested "{check}" """, fg="red")
            exit(1)

    check_single_or_plural = f"""check{"s" if ("all" in checks or len(checks) > 1) else ""}"""


    click.secho(f"""\n>>> Preparing CloudFormation templates\n""", fg="yellow")
    os.chdir(f"{BASE_DIR}/tests/test-application")
    ctx.invoke(make_config, config_file="bootstrap.yml")
    ctx.invoke(make_storage, storage_config_file="storage.yml")

    click.secho(f"""\n>>> Running {running_checks} {check_single_or_plural}\n""", fg="yellow")

    failed_checks = []
    for check_name in checks:
        if (check_name in valid_checks().keys()):
            try:
                ctx.invoke(valid_checks()[check_name])
            except CheckCloudformationFailure as error:
                failed_checks.append(error)

    if len(failed_checks) > 0:
        click.secho("The CloudFormation templates did not pass the following checks:", fg="red")
        for failed_check in failed_checks:
            click.secho(f"  - {failed_check}", fg="red")
        exit(1)
    else:
        click.secho("The CloudFormation templates passed all the checks :-)", fg="green")
