import os
import shutil

from click.testing import CliRunner
from pathlib import Path

from commands.check_cloudformation import check_cloudformation as check_cloudformation_command

BASE_DIR = Path(__file__).parent.parent


def test_runs_all_checks_when_given_no_arguments():
    result = CliRunner().invoke(check_cloudformation_command)

    assert ">>> Running all checks" in result.output
    assert ">>> Running lint check" in result.output


def test_prepares_cloudformation_templates():
    def path_exists(path):
        return os.path.exists(path) == 1

    copilot_directory = f"{BASE_DIR}/tests/test-application/copilot"
    if path_exists(copilot_directory):
        shutil.rmtree(copilot_directory)
    assert not path_exists(copilot_directory), "copilot directory should not exist"

    CliRunner().invoke(check_cloudformation_command)

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
