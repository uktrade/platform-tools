import click


def abort_with_error(message):
    click.secho(f"Error: {message}", err=True, fg="red")
    exit(1)
