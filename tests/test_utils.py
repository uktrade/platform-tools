import boto3
import click
import pytest
from click.testing import CliRunner
from moto import mock_ssm
from schema import SchemaError

from dbt_copilot_helper.exceptions import ValidationException
from dbt_copilot_helper.utils import ClickDocOptCommand
from dbt_copilot_helper.utils import ClickDocOptGroup
from dbt_copilot_helper.utils import check_aws_conn
from dbt_copilot_helper.utils import get_ssm_secrets
from dbt_copilot_helper.utils import set_ssm_param
from dbt_copilot_helper.utils import validate_string


def test_check_aws_conn_profile_not_configured(capsys):
    with pytest.raises(SystemExit):
        check_aws_conn("foo")

    captured = capsys.readouterr()

    assert """AWS profile "foo" is not configured.""" in captured.out


@mock_ssm
def test_get_ssm_secrets():
    mocked_ssm = boto3.client("ssm")
    mocked_ssm.put_parameter(
        Name="/copilot/test-application/development/secrets/TEST_SECRET",
        Description="A test parameter",
        Value="test value",
        Type="SecureString",
    )

    result = get_ssm_secrets("test-application", "development")

    assert result == [("/copilot/test-application/development/secrets/TEST_SECRET", "test value")]


@pytest.mark.parametrize(
    "overwrite, exists",
    [(False, False), (False, True)],
)
@mock_ssm
def test_set_ssm_param(overwrite, exists):
    mocked_ssm = boto3.client("ssm")

    set_ssm_param(
        "test-application",
        "development",
        "/copilot/test-application/development/secrets/TEST_SECRET",
        "random value",
        overwrite,
        exists,
        "Created for testing purposes.",
    )

    params = dict(
        Path="/copilot/test-application/development/secrets/",
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    result = mocked_ssm.get_parameters_by_path(**params)["Parameters"][0]

    expected_response = {
        "ARN": "arn:aws:ssm:eu-west-2:123456789012:parameter/copilot/test-application/development/secrets/TEST_SECRET",
        "Name": "/copilot/test-application/development/secrets/TEST_SECRET",
        "Type": "SecureString",
        "Value": "random value",
    }

    # assert result is a superset of expected_response
    assert result.items() >= expected_response.items()


@mock_ssm
def test_set_ssm_param_with_existing_secret():
    mocked_ssm = boto3.client("ssm")

    mocked_ssm.put_parameter(
        Name="/copilot/test-application/development/secrets/TEST_SECRET",
        Description="A test parameter",
        Value="test value",
        Type="SecureString",
    )

    params = dict(
        Path="/copilot/test-application/development/secrets/",
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    assert mocked_ssm.get_parameters_by_path(**params)["Parameters"][0]["Value"] == "test value"

    set_ssm_param(
        "test-application",
        "development",
        "/copilot/test-application/development/secrets/TEST_SECRET",
        "overwritten value",
        True,
        True,
        "Created for testing purposes.",
    )

    result = mocked_ssm.get_parameters_by_path(**params)["Parameters"][0]["Value"]

    assert result != "test value"
    assert result == "overwritten value"


@mock_ssm
def test_set_ssm_param_with_overwrite_but_not_exists():
    mocked_ssm = boto3.client("ssm")

    mocked_ssm.put_parameter(
        Name="/copilot/test-application/development/secrets/TEST_SECRET",
        Description="A test parameter",
        Value="test value",
        Type="SecureString",
    )

    params = dict(
        Path="/copilot/test-application/development/secrets/",
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    assert mocked_ssm.get_parameters_by_path(**params)["Parameters"][0]["Value"] == "test value"

    with pytest.raises(ValidationException) as exception:
        set_ssm_param(
            "test-application",
            "development",
            "/copilot/test-application/development/secrets/TEST_SECRET",
            "overwritten value",
            True,
            False,
            "Created for testing purposes.",
        )

    assert (
        """Arguments "overwrite" is set to True, but "exists" is set to False."""
        == exception.value.args[0]
    )


@mock_ssm
def test_set_ssm_param_tags():
    mocked_ssm = boto3.client("ssm")

    set_ssm_param(
        "test-application",
        "development",
        "/copilot/test-application/development/secrets/TEST_SECRET",
        "random value",
        False,
        False,
        "Created for testing purposes.",
    )

    parameters = mocked_ssm.describe_parameters(
        ParameterFilters=[
            {"Key": "tag:copilot-application", "Values": ["test-application"]},
            {"Key": "tag:copilot-environment", "Values": ["development"]},
        ]
    )["Parameters"]

    assert len(parameters) == 1
    assert parameters[0]["Name"] == "/copilot/test-application/development/secrets/TEST_SECRET"

    response = mocked_ssm.describe_parameters(ParameterFilters=[{"Key": "tag:copilot-application"}])

    assert len(response["Parameters"]) == 1
    assert {parameter["Name"] for parameter in response["Parameters"]} == {
        "/copilot/test-application/development/secrets/TEST_SECRET"
    }


@mock_ssm
def test_set_ssm_param_tags_with_existing_secret():
    mocked_ssm = boto3.client("ssm")

    secret_name = "/copilot/test-application/development/secrets/TEST_SECRET"
    tags = [
        {"Key": "copilot-application", "Value": "test-application"},
        {"Key": "copilot-environment", "Value": "development"},
    ]

    mocked_ssm.put_parameter(
        Name=secret_name,
        Description="A test parameter",
        Value="test value",
        Type="SecureString",
        Tags=tags,
    )

    assert (
        tags
        == mocked_ssm.list_tags_for_resource(ResourceType="Parameter", ResourceId=secret_name)[
            "TagList"
        ]
    )

    set_ssm_param(
        "test-application",
        "development",
        secret_name,
        "random value",
        True,
        True,
        "Created for testing purposes.",
    )

    assert (
        tags
        == mocked_ssm.list_tags_for_resource(ResourceType="Parameter", ResourceId=secret_name)[
            "TagList"
        ]
    )


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


@pytest.mark.parametrize(
    "regex_pattern, valid_string, invalid_string",
    [(r"^\d+-\d+$", "1-10", "20-21-23"), (r"^\d+s$", "10s", "10seconds")],
)
def test_validate_string(regex_pattern, valid_string, invalid_string):
    validator = validate_string(regex_pattern)

    assert validator(valid_string) == valid_string

    with pytest.raises(SchemaError) as err:
        validator(invalid_string)

    assert err.value.args[0] == f"String '{invalid_string}' does not match the required pattern."
