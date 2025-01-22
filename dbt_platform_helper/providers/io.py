import click

from dbt_platform_helper.platform_exception import PlatformException


class ClickIOProvider:
    @staticmethod
    def warn(message: str):
        click.secho(message, fg="yellow")

    @staticmethod
    def error(message: str):
        click.secho(message, fg="red")

    @staticmethod
    def info(message: str):
        click.secho(message)

    @staticmethod
    def input(message: str) -> str:
        return click.prompt(message)

    @staticmethod
    def confirm(message: str) -> bool:
        try:
            return click.confirm(message)
        except click.Abort as e:
            raise ClickIOProviderException(message + " [y/N]: Error: invalid input")


class ClickIOProviderException(PlatformException):
    pass
