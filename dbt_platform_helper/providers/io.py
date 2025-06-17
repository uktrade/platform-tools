import click

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.environment_variable import (
    EnvironmentVariableProvider,
)


class ClickIOProvider:
    def __init__(self, env_var_provider=EnvironmentVariableProvider()):
        self.env_var_provider = env_var_provider
        self.debug_flag = self.env_var_provider.get("DEBUG")

    def warn(self, message: str):
        click.secho(message, fg="magenta")

    def debug(self, message: str):
        if self.debug_flag and self.debug_flag.strip().upper() == "TRUE":
            click.secho(message, fg="green")

    def error(self, message: str):
        click.secho(f"Error: {message}", fg="red")

    def info(self, message: str, **kwargs):
        click.secho(message, **kwargs)

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

    # TODO: DBTP-1979: messages will be a ValidationMessages class rather than a free-rein dictionary
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
