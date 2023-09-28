from subprocess import run

import click


def get_lint_result(path: str, ignore_path: str = None, ignore_checks: str = None):
    command = ["cfn-lint", path]
    if ignore_path:
        command.extend(["--ignore-templates", ignore_path])
    if ignore_checks:
        command.extend(["--ignore-checks", ignore_checks])

    click.secho(f"\n>>> Running lint check", fg="yellow")
    click.secho(f"""    {" ".join(command)}\n""", fg="yellow")

    return run(command, capture_output=True)
