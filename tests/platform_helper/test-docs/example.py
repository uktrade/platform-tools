#!/usr/bin/env python

import click

from dbt_platform_helper.utils.click import ClickDocOptCommand
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup)
def cli():
    pass


@click.group(chain=True, cls=ClickDocOptGroup)
def great_greets():
    pass


@great_greets.command(cls=ClickDocOptCommand)
@click.option("--count", default=1, help="number of greetings")
@click.argument("name")
def hello(count, name):
    for x in range(count):
        click.echo(f"Hello {name}!")


@great_greets.command(cls=ClickDocOptCommand)
@click.argument("app")
@click.argument("env")
@click.argument("svc")
def argument_replacements(app, env, svc):
    click.echo(f"app: {app}, env: {env}, svc: {svc}")


@great_greets.command(cls=ClickDocOptCommand)
@click.option("--app")
@click.option("--env")
@click.option("--svc")
def option_replacements(app, env, svc):
    click.echo(f"app: {app}, env: {env}, svc: {svc}")


cli.add_command(great_greets)


if __name__ == "__main__":
    cli()
