from unittest.mock import patch

import pytest
from click.testing import CliRunner

import commands
from commands.check_cloudformation import check_cloudformation as check_cloudformation_command, valid_checks


@pytest.fixture
def valid_checks_dict():
    return {
        "one": lambda: "Check one output",
        "two": lambda: "Check two output",
        "three": lambda: "Check three output",
        "four": lambda: "Check four output",
    }


@patch("commands.check_cloudformation.valid_checks")
def test_exits_if_invalid_check_specified(valid_checks_mock, valid_checks_dict):
    runner = CliRunner()
    valid_checks_mock.return_value = valid_checks_dict

    result = runner.invoke(check_cloudformation_command, ["does-not-exist"])

    assert result.exit_code == 1
    assert isinstance(result.exception, ValueError)
    assert '''Invalid check requested in "does-not-exist"''' in str(result.exception)


test_data = [
    (["one"], "Running one check", ["Check one output"]),
    (["two"], "Running two check", ["Check two output"]),
    (["one", "two"], "Running one & two check", ["Check two output"]),
    (["one", "three", "four"], "Running one, three & four checks", ["Check one output"]),
]
@patch("commands.check_cloudformation.valid_checks")
@pytest.mark.parametrize("requested_checks, expect_check_plan, expected_check_outputs", test_data)
def test_runs_checks_from_arguments(
        valid_checks_mock,
        valid_checks_dict,
        requested_checks,
        expect_check_plan,
        expected_check_outputs
):
    runner = CliRunner()
    valid_checks_mock.return_value = valid_checks_dict

    result = runner.invoke(check_cloudformation_command, requested_checks)

    assert result.exit_code == 0
    assert expect_check_plan in result.output
    for expected_check_output in expected_check_outputs:
        assert expected_check_output in result.output


@patch("commands.check_cloudformation.valid_checks")
def test_runs_all_checks_when_given_no_arguments(valid_checks_mock, valid_checks_dict):
    runner = CliRunner()
    valid_checks_mock.return_value = valid_checks_dict

    result = runner.invoke(check_cloudformation_command)

    assert result.exit_code == 0
    assert "Running all checks" in result.output
    assert "Check one output" in result.output
    assert "Check two output" in result.output
    assert "Check three output" in result.output
    assert "Check four output" in result.output
