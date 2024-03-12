#!/usr/bin/env python

import click

from dbt_platform_helper.utils.click import ClickDocOptCommand
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.command(cls=ClickDocOptCommand)
@click.option("--count", default=1, help="number of greetings")
@click.argument("name")
def hello(count, name):
    for x in range(count):
        click.echo(f"Hello {name}!")


@click.command(cls=ClickDocOptCommand)
@click.argument("app")
@click.argument("env")
@click.argument("svc")
def argument_replacements(app, env, svc):
    click.echo(f"app: {app}, env: {env}, svc: {svc}")


@click.command(cls=ClickDocOptCommand)
@click.option("--app")
@click.option("--env")
@click.option("--svc")
def option_replacements(app, env, svc):
    click.echo(f"app: {app}, env: {env}, svc: {svc}")


@click.group(cls=ClickDocOptGroup)
def cli():
    pass


cli.add_command(hello)
cli.add_command(argument_replacements)
cli.add_command(option_replacements)


if __name__ == "__main__":
    cli()
