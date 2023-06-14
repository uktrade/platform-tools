import os
import shutil
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from pathlib import Path

from commands.check_cloudformation import check_cloudformation as check_cloudformation_command


BASE_DIR = Path(__file__).parent.parent


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


@patch("commands.check_cloudformation.valid_checks")
def test_prepares_cloudformation_templates(valid_checks_mock, valid_checks_dict):
    def path_exists(path):
        return os.path.exists(path) == 1

    runner = CliRunner()
    valid_checks_mock.return_value = valid_checks_dict
    copilot_directory = f"{BASE_DIR}/tests/test-application/copilot"
    if path_exists(copilot_directory):
        shutil.rmtree(copilot_directory)
    assert not path_exists(copilot_directory), "copilot directory should not exist"

    runner.invoke(check_cloudformation_command)

    assert path_exists(copilot_directory), "copilot directory should exist"
    expected_sub_directories = [
        "celery",
        "environments",
        "environments/addons",
        "environments/development",
        "environments/production",
        "environments/staging",
        "s3proxy",
        "web",
        "web/addons",
    ]
    for expected_sub_directory in expected_sub_directories:
        path = f"{copilot_directory}/{expected_sub_directory}"
        assert path_exists(path), f"copilot/{expected_sub_directory} should exist"



