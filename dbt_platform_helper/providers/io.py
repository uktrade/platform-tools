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

    # TODO messages will be a ValidationMessages class rather than a free-rein dictionary
    def process_messages(self, messages: dict):
        if not messages:
            return

        if messages.get("errors"):
            self.error("\n".join(messages["errors"]))

        if messages.get("warnings"):
            self.warn("\n".join(messages["warnings"]))

        if messages.get("info"):
            self.info("\n".join(messages["info"]))


class ClickIOProviderException(PlatformException):
    pass
