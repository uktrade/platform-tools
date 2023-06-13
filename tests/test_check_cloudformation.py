from unittest.mock import patch

import pytest
from click.testing import CliRunner

import commands
from commands.check_cloudformation import check_cloudformation as check_cloudformation_command, valid_checks


@pytest.fixture
def valid_checks_dict():
    return {
        "all": lambda: None,
        "one": lambda: "Check one output",
        "two": lambda: "Check two output",
    }


@patch("commands.check_cloudformation.valid_checks")
def test_exit_if_no_check_specified(valid_checks_mock, valid_checks_dict):
    runner = CliRunner()
    valid_checks_mock.return_value = valid_checks_dict

    result = runner.invoke(check_cloudformation_command)

    assert result.exit_code == 2
    assert "Error: Missing argument 'CHECK'" in result.output


@patch("commands.check_cloudformation.valid_checks")
def test_exit_if_invalid_check_specified(valid_checks_mock, valid_checks_dict):
    runner = CliRunner()
    valid_checks_mock.return_value = valid_checks_dict

    result = runner.invoke(check_cloudformation_command, ["does-not-exist"])

    assert result.exit_code == 1
    assert isinstance(result.exception, ValueError)
    assert "Invalid value (does-not-exist) for 'CHECK'" in str(result.exception)


test_data = [
    ("one", "Check one output"),
    ("two", "Check two output"),
]


@patch("commands.check_cloudformation.valid_checks")
@pytest.mark.parametrize("requested_check, expected_check_output", test_data)
def test_runs_specific_check_when_given_check(
        valid_checks_mock,
        valid_checks_dict,
        requested_check,
        expected_check_output
):
    runner = CliRunner()
    valid_checks_mock.return_value = valid_checks_dict

    result = runner.invoke(check_cloudformation_command, [requested_check])

    assert result.exit_code == 0
    assert f"Running {requested_check} check" in result.output
    assert expected_check_output in result.output


@patch("commands.check_cloudformation.valid_checks")
def test_runs_all_checks_when_given_all(valid_checks_mock, valid_checks_dict):
    runner = CliRunner()
    valid_checks_mock.return_value = valid_checks_dict

    result = runner.invoke(check_cloudformation_command, ["all"])

    assert result.exit_code == 0
    assert "Running all checks" in result.output
    assert "Check one output" in result.output
    assert "Check two output" in result.output
