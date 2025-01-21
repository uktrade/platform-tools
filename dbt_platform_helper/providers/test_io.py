import click

from dbt_platform_helper.providers.io import IOProvider


class TestIOProvider:
    def test_warning(self, capsys):
        io_provider = IOProvider(click.secho, click.secho, click.confirm)
        io_provider.warn("Beware!")
        captured = str(capsys.readouterr())
        assert "Beware!" in captured
