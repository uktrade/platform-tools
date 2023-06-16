from pathlib import Path
from shutil import copyfile
from shutil import rmtree
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from commands.check_cloudformation import \
    check_cloudformation as check_cloudformation_command
from tests.conftest import BASE_DIR


@pytest.fixture
def copilot_directory() -> Path:
    return Path(f"{BASE_DIR}/tests/test-application/copilot")


def test_runs_all_checks_when_given_no_arguments() -> None:
    result = CliRunner().invoke(check_cloudformation_command)

    assert ">>> Running all checks" in result.output
    assert ">>> Running lint check" in result.output


def test_prepares_cloudformation_templates(copilot_directory: Path) -> None:
    ensure_directory_does_not_exist(copilot_directory)

    CliRunner().invoke(check_cloudformation_command)

    assert copilot_directory.exists(), "copilot directory should exist and include cloudformation templates"
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
        path = Path(f"{copilot_directory}/{expected_path}")
        assert path.exists(), f"copilot/{expected_path} should exist"


def ensure_directory_does_not_exist(copilot_directory: Path) -> None:
    if copilot_directory.exists():
        rmtree(copilot_directory)
    assert not copilot_directory.exists(), "copilot directory should not exist"


def prepare_fake_cloudformation_templates(copilot_directory: Path, passing: str) -> None:
    template = "valid_cloudformation_template.yml" if passing else "invalid_cloudformation_template.yml"
    ensure_directory_does_not_exist(copilot_directory)
    addons_directory = Path(f"{BASE_DIR}/tests/test-application/copilot/environments/addons")
    addons_directory.mkdir(parents=True, exist_ok=True)
    copyfile(f"{BASE_DIR}/tests/fixtures/{template}", f"{addons_directory}/{template}")


@patch("commands.check_cloudformation.prepare_cloudformation_templates")
def test_outputs_passed_results_summary(patched_prepare_cloudformation_templates, copilot_directory: Path) -> None:
    patched_prepare_cloudformation_templates.return_value(None)
    prepare_fake_cloudformation_templates(copilot_directory, passing=True)

    result = CliRunner().invoke(check_cloudformation_command)

    assert (
        "The CloudFormation templates passed the following checks :-)\n  - lint" in result.output
    ), "The passed checks summary was not outputted"


@patch("commands.check_cloudformation.prepare_cloudformation_templates")
def test_outputs_failed_results_summary(patched_prepare_cloudformation_templates, copilot_directory: Path) -> None:
    patched_prepare_cloudformation_templates.return_value(None)
    prepare_fake_cloudformation_templates(copilot_directory, passing=False)

    result = CliRunner().invoke(check_cloudformation_command)

    assert (
        "The CloudFormation templates failed the following checks :-(\n  - lint" in result.output
    ), "The failed checks summary was not outputted"
