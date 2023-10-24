import click


def abort_with_error(message):
    click.secho(f"Error: {message}", fg="red")
    exit(1)
