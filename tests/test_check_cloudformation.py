import os
import shutil
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from pathlib import Path

from commands.check_cloudformation import check_cloudformation as check_cloudformation_command
from commands.exceptions.CheckCloudformationFailure import CheckCloudformationFailure

BASE_DIR = Path(__file__).parent.parent

def mock_check(output, failure=None):
    def mocked_check():
        print(output)
        if failure:
            raise CheckCloudformationFailure(failure)

    return mocked_check


@pytest.fixture
def valid_checks_dict():
    return {
        "one": mock_check("Check one output"),
        "two": mock_check("Check two output"),
        "three": mock_check("Check three output"),
        "four": mock_check("Check four output"),
    }


@patch("commands.check_cloudformation.valid_checks")
def test_exits_if_invalid_check_specified(valid_checks_mock, valid_checks_dict):
    runner = CliRunner()
    valid_checks_mock.return_value = valid_checks_dict

    result = runner.invoke(check_cloudformation_command, ["does-not-exist", "one"])

    assert result.exit_code == 1
    assert '''Invalid check requested "does-not-exist"''' in str(result.output)


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
    assert "The CloudFormation templates passed all the checks" in result.output


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
    assert "The CloudFormation templates passed all the checks" in result.output


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

    assert path_exists(copilot_directory), "copilot directory should exist and include cloudformation templates"
    expected_paths = [
        "celery",
        "environments",
        "environments/addons",
        "environments/addons/my-aurora-db.yml",
        "environments/addons/my-opensearch.yml",
        "environments/addons/my-rds-db.yml",
        "environments/addons/my-redis.yml",
        "environments/addons/my-s3-bucket.yml",
        "environments/development",
        "environments/production",
        "environments/staging",
        "s3proxy",
        "s3proxy/addons",
        "s3proxy/addons/ip-filter.yml",
        "web",
        "web/addons",
        "web/addons/ip-filter.yml",
        "web/addons/my-s3-bucket.yml",
        "web/addons/my-s3-bucket-bucket-access.yml",
    ]
    for expected_path in expected_paths:
        path = f"{copilot_directory}/{expected_path}"
        assert path_exists(path), f"copilot/{expected_path} should exist"

@patch("commands.check_cloudformation.valid_checks")
def test_exits_with_errors_if_checks_fail(valid_checks_mock, valid_checks_dict):
    runner = CliRunner()
    valid_checks_dict["fail1"] = mock_check("Check fail1 output", "Failing check1 error")
    valid_checks_dict["fail2"] = mock_check("Check fail2 output", "Failing check2 error")
    valid_checks_mock.return_value = valid_checks_dict

    result = runner.invoke(check_cloudformation_command, ["one", "fail1", "two", "fail2"], catch_exceptions=False)

    assert result.exit_code == 1
    assert "Check one output" in result.output
    assert "Check fail1 output" in result.output
    assert "Check two output" in result.output
    assert "Check fail2 output" in result.output
    assert "CheckCloudformationFailure" not in result.output
    assert "The CloudFormation templates did not pass the following checks:" in result.output
    assert "- Failing check1 error" in result.output
    assert "- Failing check2 error" in result.output

