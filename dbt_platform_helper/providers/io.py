import click

from dbt_platform_helper.platform_exception import PlatformException


class ClickIOProvider:
    def warn(message: str):
        click.secho(message, fg="yellow")

    def error(message: str):
        click.secho(message, fg="red")

    def info(message: str):
        click.secho(message)

    def input(message: str) -> str:
        return click.prompt(message)

    def confirm(message: str) -> bool:
        try:
            return click.confirm(message)
        except click.Abort as e:
            raise ClickIOProviderException(message + " [y/N]: Error: invalid input")


class ClickIOProviderException(PlatformException):
    pass
