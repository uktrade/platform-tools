#!/usr/bin/env python
import os
from pathlib import Path
from subprocess import run

import click

from commands.bootstrap_cli import make_config
from commands.exceptions.CheckCloudformationFailure import CheckCloudformationFailure
from commands.copilot_cli import make_storage

BASE_DIR = Path(__file__).parent.parent


def valid_checks():
    return {
        "lint": lint,
    }


@click.group(invoke_without_command=True)
@click.argument("checks", nargs=-1)
@click.pass_context
def check_cloudformation(ctx, checks):
    """Runs the checks passed in the command arguments. If no argument is passed, it will run all the checks."""

    if not checks:
        checks = valid_checks()
        running_checks = "all"
    else:
        running_checks = ' & '.join(', '.join(checks).rsplit(', ', 1))

    for check in checks:
        if check not in valid_checks():
            click.secho(f"""Invalid check requested "{check}" """, fg="red")
            click.echo(ctx.get_help())
            exit(1)

    check_single_or_plural = f"""check{"s" if (running_checks == "all" or len(checks) > 1) else ""}"""


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

    if failed_checks:
        click.secho("The CloudFormation templates did not pass the following checks:", fg="red")
        for failed_check in failed_checks:
            click.secho(f"  - {failed_check}", fg="red")
        exit(1)
    else:
        click.secho("The CloudFormation templates passed all the checks :-)", fg="green")


@check_cloudformation.command()
def lint():
    """Runs cfn-lint against the generated CloudFormation templates."""

    BASE_DIR = Path(__file__).parent.parent

    command = ["cfn-lint", f"{BASE_DIR}/tests/test-application/copilot/**/addons/*.yml"]

    click.secho(f"""\nRunning {" ".join(command)}\n""")

    result = run(command, capture_output=True)

    click.secho(result.stdout.decode())
    if result.returncode != 0:
        click.secho(result.stderr.decode())

    if result.returncode != 0:
        raise CheckCloudformationFailure("cfn-lint failed")
