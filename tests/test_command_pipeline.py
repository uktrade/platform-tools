import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from dbt_copilot_helper.commands.pipeline import generate
from tests.conftest import EXPECTED_FILES_DIR
from tests.conftest import FIXTURES_DIR
from tests.conftest import mock_codestar_connections_boto_client


@patch("boto3.client")
def test_pipeline_generate_with_git_repo_creates_the_pipeline_configuration(
    mocked_boto3_client, tmp_path
):
    mock_codestar_connections_boto_client(mocked_boto3_client, ["test-app"])

    os.chdir(tmp_path)
    shutil.copy(FIXTURES_DIR / "valid_bootstrap_config.yml", "bootstrap.yml")
    shutil.copy(FIXTURES_DIR / "pipeline/pipelines.yml", "pipelines.yml")
    subprocess.run(["git", "init"])
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:uktrade/test-app.git"])

    relative_dir_path = "copilot/pipelines/test-app-environments"
    output_dir = tmp_path / relative_dir_path
    buildspec = output_dir / "buildspec.yml"
    manifest = output_dir / "manifest.yml"
    cfn_patch = output_dir / "overrides" / "cfn.patches.yml"

    exp_files_dir = Path(EXPECTED_FILES_DIR) / "pipeline" / "pipelines" / "test-app-environments"
    exp_buildspec = (exp_files_dir / "buildspec.yml").read_text()
    exp_manifest = (exp_files_dir / "manifest.yml").read_text()
    exp_cfn_patch = (exp_files_dir / "overrides" / "cfn.patches.yml").read_text()

    result = CliRunner().invoke(generate)

    assert buildspec.read_text() == exp_buildspec
    assert manifest.read_text() == exp_manifest
    assert cfn_patch.read_text() == exp_cfn_patch
    assert f"File {relative_dir_path}/buildspec.yml created" in result.stdout
    assert f"File {relative_dir_path}/manifest.yml created" in result.stdout
    assert f"File {relative_dir_path}/overrides/cfn.patches.yml created" in result.stdout


def test_pipeline_generate_with_no_codestar_connection_exits_with_failure_message(tmp_path):
    pass


def test_pipeline_generate_with_http_repo_creates_the_pipeline_configuration(tmp_path):
    pass


def test_pipeline_generate_with_no_repo_fails_with_a_message(tmp_path):
    pass
