import click

from dbt_platform_helper.platform_exception import PlatformException


class ClickIOProvider:
    def warn(self, message: str):
        click.secho(message, fg="magenta")

    def error(self, message: str):
        click.secho(f"Error: {message}", fg="red")

    def info(self, message: str):
        click.secho(message)

    def input(self, message: str) -> str:
        return click.prompt(message)

    def confirm(self, message: str) -> bool:
        try:
            return click.confirm(message)
        except click.Abort:
            raise ClickIOProviderException(message + " [y/N]: Error: invalid input")

    def abort_with_error(self, message: str):
        click.secho(f"Error: {message}", err=True, fg="red")
        exit(1)


class ClickIOProviderException(PlatformException):
    pass
