import click

from dbt_platform_helper.platform_exception import PlatformException


class ClickIOProvider:
    def warn(self, message: str):
        click.secho(message, fg="orange")

    def error(self, message: str):
        click.secho(message, fg="red")

    def info(self, message: str):
        click.secho(message)

    def input(self, message: str) -> str:
        return click.prompt(message)

    def confirm(self, message: str) -> bool:
        try:
            return click.confirm(message)
        except click.Abort as e:
            raise ClickIOProviderException(message + " [y/N]: Error: invalid input")


class ClickIOProviderException(PlatformException):
    pass
