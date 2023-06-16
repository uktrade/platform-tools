import os
import shutil
from pathlib import Path

from click.testing import CliRunner

from commands.check_cloudformation import check_cloudformation as check_cloudformation_command
from tests.conftest import BASE_DIR


def test_runs_all_checks_when_given_no_arguments():
    result = CliRunner().invoke(check_cloudformation_command)

    assert ">>> Running all checks" in result.output
    assert ">>> Running lint check" in result.output


def test_prepares_cloudformation_templates():
    copilot_directory = Path(f"{BASE_DIR}/tests/test-application/copilot")
    if copilot_directory.exists():
        shutil.rmtree(copilot_directory)
    assert not copilot_directory.exists(), "copilot directory should not exist"

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
