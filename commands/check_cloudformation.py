#!/usr/bin/env python
import os
from pathlib import Path
from shutil import rmtree
from subprocess import run

import click

from commands.bootstrap_cli import make_config
from commands.copilot_cli import make_storage

BASE_DIR = Path(__file__).parent.parent


@click.group(invoke_without_command=True, chain=True)
@click.pass_context
def check_cloudformation(ctx: click.Context) -> None:
    """
    Runs the checks passed in the command arguments.

    If no argument is passed, it will run all the checks.
    """

    ctx.obj = {"passing_checks": [], "failing_checks": []}

    prepare_cloudformation_templates(ctx)

    if ctx.invoked_subcommand is None:
        click.secho(f"\n>>> Running all checks", fg="yellow")
        for name, command in ctx.command.commands.items():
            ctx.invoke(command)


def get_lint_result(path: str):
    command = [
        "cfn-lint",
        path,
        "--ignore-templates",
        # addons.parameters.yml is not a CloudFormation template file
        f"{BASE_DIR}/tests/test-application/copilot/**/addons/addons.parameters.yml",
    ]

    click.secho(f"\n>>> Running lint check", fg="yellow")
    click.secho(f"""    {" ".join(command)}\n""", fg="yellow")

    return run(command, capture_output=True)


@check_cloudformation.command()
@click.pass_context
def lint(ctx: click.Context) -> None:
    """Runs cfn-lint against the generated CloudFormation templates."""

    BASE_DIR = Path(__file__).parent.parent

    result = get_lint_result(f"{BASE_DIR}/tests/test-application/copilot/**/addons/*.yml")

    click.secho(result.stdout.decode())
    if result.returncode == 0:
        ctx.obj["passing_checks"].append("lint")
    else:
        click.secho(result.stderr.decode())
        ctx.obj["failing_checks"].append("lint")


@check_cloudformation.result_callback()
@click.pass_context
def process_result(ctx: click.Context, result) -> None:
    if ctx.obj["passing_checks"]:
        click.secho("\nThe CloudFormation templates passed the following checks :-)", fg="green")
        for passing_check in ctx.obj["passing_checks"]:
            click.secho(f"  - {passing_check}", fg="green")

    if ctx.obj["failing_checks"]:
        click.secho("\nThe CloudFormation templates failed the following checks :-(", fg="red")
        for failing_check in ctx.obj["failing_checks"]:
            click.secho(f"  - {failing_check}", fg="red")
        exit(1)


def prepare_cloudformation_templates(ctx: click.Context) -> None:
    click.secho(f"\n>>> Preparing CloudFormation templates\n", fg="yellow")
    os.chdir(f"{BASE_DIR}/tests/test-application")
    copilot_directory = Path("./copilot")
    if copilot_directory.exists():
        rmtree(copilot_directory)
    ctx.invoke(make_config)
    ctx.invoke(make_storage)
