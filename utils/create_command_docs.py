#!/usr/bin/env python

import importlib
from pathlib import Path
from typing import Any
from typing import Generator
from typing import List
from typing import NamedTuple
from typing import Optional

import click

from dbt_copilot_helper.utils.template import setup_templates


class Parameter(NamedTuple):
    """Command parameter definition."""

    default: Any
    name: str
    param_type_name: str
    required: bool
    type_name: str
    usage: str
    help: Optional[str] = None
    prompt: Optional[str] = None


class CommandMetadata(NamedTuple):
    """Command metadata definition."""

    arguments: List[Parameter]
    description: Optional[str]
    help: str
    name: str
    options: List[Parameter]
    parent_reference: str
    subcommands: Optional[Any]
    usage: str


def get_cmd_metadata(
    cmd: click.core.Command,
    parent: Optional[click.core.Context] = None,
    command_name: Optional[str] = None,
) -> Generator[CommandMetadata, None, None]:
    """
    Get command metadata recursively.

    Parameters:
        cmd (click.core.Command): Command from which the metadata will be parsed.
        parent (Context, optional): Parent command context.
        command_name (str, optional): Command name.

    Yields:
        CommandMetadata: Command metadata.
    """

    context = click.core.Context(cmd, info_name=cmd.name, parent=parent)
    parent_reference = f"#{command_name.replace(' ', '-').lower()}" if command_name else ""

    command_name = f"{command_name + ' ' if command_name else ''}{str(cmd.name)}"

    subcommands = cmd.to_info_dict(context).get("commands", {})
    subcommands_names = getattr(cmd, "commands", {})

    for subcommand in subcommands_names:
        subcommands[subcommand]["link"] = f"#{command_name.replace(' ', '-').lower()}-{subcommand}"

    params = [
        Parameter(
            default=param.default,
            help=param.help if isinstance(param, click.core.Option) else None,
            name=param.name or "",
            param_type_name=param.param_type_name,
            prompt=param.prompt if isinstance(param, click.core.Option) else None,
            required=param.required,
            type_name=param.type.name,
            usage="\n".join(param.opts),
        )
        for param in cmd.get_params(context)
    ]

    yield CommandMetadata(
        arguments=[param for param in params if param.param_type_name == "argument"],
        description=cmd.help,
        help=cmd.get_help(context),
        name=command_name,
        options=[param for param in params if param.param_type_name == "option"],
        parent_reference=parent_reference,
        subcommands=subcommands,
        # Strip "Usage: " (7 characters) and re-indent each line to match
        usage="\n".join(
            map(
                lambda x: x[7:],
                cmd.get_usage(context)
                .replace("<app>", "<application>")
                .replace("<env>", "<environment>")
                .replace("<svc>", "<service>")
                .split("\n"),
            )
        ),
    )

    for sub in subcommands_names.values():
        yield from get_cmd_metadata(sub, context, command_name)


def create_docs(base_command, output):
    """Create Markdown documentation from Click command metadata."""

    templates = setup_templates()
    content = dict(
        toc=[command.name for command in get_cmd_metadata(base_command)],
        metadata=get_cmd_metadata(base_command),
    )

    with open(output, "w") as md_file:
        md_file.write(templates.get_template("COMMANDS.md.jinja").render(content))


@click.command()
@click.option("--module", "-m", help="The base command module path to import", required=True)
@click.option("--cmd", "-c", help="The base command function to import", required=True)
@click.option(
    "--output",
    "-o",
    help="The output filename to write the md file",
    required=True,
    type=click.Path(),
)
def docs(module, cmd, output):
    """Create Markdown documentation file from click CLI."""

    click.secho(f"Creating Markdown docs from {module}.{cmd}", fg="green")

    try:
        module_ = importlib.import_module(module)
    except (ModuleNotFoundError, NameError) as e:
        raise click.ClickException(f"Could not find module: {module}. Error: {str(e)}")

    try:
        command_ = getattr(module_, cmd)
    except AttributeError:
        raise click.ClickException(f"Could not find command {cmd} in {module} module")

    try:
        create_docs(command_, output=Path(output))
        click.secho(f"Markdown docs have been successfully saved to {output}", fg="green")
    except Exception as e:
        raise click.ClickException(f"Dumps command failed: {str(e)}")


if __name__ == "__main__":
    docs()
