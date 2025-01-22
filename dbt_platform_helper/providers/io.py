import click


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
        return click.confirm(message)
