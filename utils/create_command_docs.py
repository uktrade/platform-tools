#!/usr/bin/env python

import importlib
from pathlib import Path
from typing import Any
from typing import Generator
from typing import List
from typing import NamedTuple
from typing import Optional

import click

TEMPLATE = """
# {command_name}

{parent}

{description}

## Usage

```
{usage}
```

## Options

{options}

{commands}

## CLI Help

```
{help}
```
"""


class Parameter(NamedTuple):
    """Command parameter definition."""

    name: str
    type_name: str
    default: Any
    usage: str
    required: bool
    prompt: Optional[str] = None
    help: Optional[str] = None


class CommandMetadata(NamedTuple):
    """Command metadata definition."""

    name: str
    help: str
    usage: str
    parent_reference: str
    params: List[Parameter]
    subcommands: Optional[Any]
    description: Optional[str]


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
            name=param.name or "",
            type_name=param.type.name,
            default=param.default,
            usage="\n".join(param.opts),
            required=param.required,
            prompt=param.prompt if isinstance(param, click.core.Option) else None,
            help=param.help if isinstance(param, click.core.Option) else None,
        )
        for param in cmd.get_params(context)
    ]

    yield CommandMetadata(
        name=command_name,
        help=cmd.get_help(context),
        usage=cmd.get_usage(context),
        description=cmd.help,
        parent_reference=parent_reference,
        params=params,
        subcommands=subcommands,
    )

    for sub in subcommands_names.values():
        yield from get_cmd_metadata(sub, context, command_name)


def create_docs(base_command, output):
    """Create Markdown documentation from Click command metadata."""

    table_of_contents = ["# Commands\n"]
    markdown_docs = []

    for meta in get_cmd_metadata(base_command):
        table_of_contents.append(f"- [{meta.name}](#{meta.name.replace(' ', '-').lower()})")

        markdown_docs.append(
            TEMPLATE.format(
                command_name=meta.name,
                parent=f"[↩ Parent]({meta.parent_reference})" if meta.parent_reference else "Base command.",
                description=meta.description if meta.description else "No description.",
                usage=meta.usage,
                options="\n".join(
                    [
                        f"- `{param.usage} <{param.type_name}>`"
                        f"{' _Defaults to ' + str(param.default) + '._' if param.default is not None else ''}"
                        f"{chr(10) if param.help is not None else ''}"
                        f"{'  -  ' + param.help if param.help is not None else ''}"
                        for param in meta.params
                    ],
                ),
                commands="## Commands\n\n"
                + "\n".join([f"- [`{cmd_name}` ↪]({opt.get('link')})" for cmd_name, opt in meta.subcommands.items()])
                if meta.subcommands
                else "No commands.",
                help=meta.help,
            ),
        )

        with open(output, "w") as md_file:
            md_file.write("\n".join(table_of_contents) + "\n")

            for markdown_doc in markdown_docs:
                md_file.write(markdown_doc)


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
