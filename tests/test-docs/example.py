#!/usr/bin/env python

import click


@click.command()
@click.option("--count", default=1, help="number of greetings")
@click.argument("name")
def hello(count, name):
    for x in range(count):
        click.echo(f"Hello {name}!")


@click.group()
def cli():
    pass


cli.add_command(hello)


if __name__ == "__main__":
    cli()
