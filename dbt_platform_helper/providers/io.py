import click


class IOProvider:
    @staticmethod
    def warn(message: str):
        pass

    @staticmethod
    def error(message: str):
        pass

    @staticmethod
    def confirm(message: str) -> bool:
        pass


class ClickIOProvider(IOProvider):
    @staticmethod
    def warn(message: str):
        click.secho(message, fg="yellow")

    @staticmethod
    def error(message: str):
        click.secho(message, fg="red")

    @staticmethod
    def confirm(message: str) -> bool:
        return click.confirm(message)
