import click
from click.testing import CliRunner

from dbt_platform_helper.utils.click import ClickDocOptCommand
from dbt_platform_helper.utils.click import ClickDocOptGroup


def test_click_docopt_command_help():
    @click.command(cls=ClickDocOptCommand)
    @click.argument("required", required=True)
    @click.argument("optional", required=False)
    @click.argument("required-choice", type=click.Choice(["req-one", "req-two"]), required=True)
    @click.argument("optional-choice", type=click.Choice(["opt-one", "opt-two"]), required=False)
    @click.option("--required-free-text", help="Required Free Text", required=True)
    @click.option("--optional-free-text", help="Optional Free Text", required=False)
    @click.option("--required-choice", type=click.Choice(["req-one", "req-two"]), required=True)
    @click.option("--optional-choice", type=click.Choice(["opt-one", "opt-two"]), required=False)
    @click.option("--flag/--no-flag", help="Boolean Flag")
    def test_help():
        pass

    result = CliRunner().invoke(test_help, ["--help"])

    assert (
        "test-help <required> (req-one|req-two) [<optional>] [(opt-one|opt-two)]" in result.output
    )
    assert (
        "--required-free-text <required_free_text> --required-choice (req-one|req-two)"
        in result.output
    )
    assert (
        "[--optional-free-text <optional_free_text>] [--optional-choice (opt-one|opt-two)]"
        in result.output
    )
    assert "[--flag]" in result.output


def test_click_docopt_command_group_usage_command():
    @click.group(cls=ClickDocOptGroup)
    def test_group():
        pass

    @test_group.command()
    def command_one():
        pass

    result = CliRunner().invoke(test_group, ["--help"])

    assert "test-group command-one" in result.output


def test_click_docopt_command_group_usage_command_choice():
    @click.group(cls=ClickDocOptGroup)
    def test_group():
        pass

    @test_group.command()
    def command_one():
        pass

    @test_group.command()
    def command_two():
        pass

    result = CliRunner().invoke(test_group, ["--help"])

    assert "test-group (command-one|command-two)" in result.output


def test_click_docopt_command_group_usage_command_many():
    @click.group(cls=ClickDocOptGroup)
    def test_group():
        pass

    @test_group.command()
    def command_one():
        pass

    @test_group.command()
    def command_two():
        pass

    @test_group.command()
    def command_three():
        pass

    @test_group.command()
    def command_four():
        pass

    @test_group.command()
    def command_five():
        pass

    result = CliRunner().invoke(test_group, ["--help"])

    assert "test-group <command>" in result.output
