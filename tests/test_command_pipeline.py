import os
import shutil
import subprocess
from pathlib import Path

from click.testing import CliRunner

from dbt_copilot_helper.commands.pipeline import generate
from tests.conftest import EXPECTED_FILES_DIR
from tests.conftest import FIXTURES_DIR


def test_pipeline_generate_with_git_repo_creates_the_pipeline_configuration(tmp_path):
    """"""
    os.chdir(tmp_path)
    shutil.copy(FIXTURES_DIR / "valid_bootstrap_config.yml", "bootstrap.yml")
    shutil.copy(FIXTURES_DIR / "pipeline/pipelines.yml", "pipelines.yml")
    subprocess.run(["git", "init"])
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:uktrade/test-app.git"])

    CliRunner().invoke(generate, ["--codestar-connection", "Test-application"])

    output_dir = tmp_path / "copilot" / "pipelines" / "test-app-environments"
    buildspec = output_dir / "buildspec.yml"
    manifest = output_dir / "manifest.yml"
    cfn_patch = output_dir / "overrides" / "cfn.patches.yml"

    assert buildspec.exists()
    assert manifest.exists()
    assert cfn_patch.exists()

    exp_files_dir = Path(EXPECTED_FILES_DIR) / "pipeline" / "pipelines" / "test-app-environments"
    exp_buildspec = (exp_files_dir / "buildspec.yml").read_text()
    exp_manifest = (exp_files_dir / "manifest.yml").read_text()
    (exp_files_dir / "overrides" / "cfn.patches.yml").read_text()

    assert buildspec.read_text() == exp_buildspec
    assert manifest.read_text() == exp_manifest
    # assert cfn_patch.read_text() == exp_cfn_patch


def test_pipeline_generate_with_http_repo_creates_the_pipeline_configuration(tmp_path):
    pass


def test_pipeline_generate_with_no_repo_fails_with_a_message(tmp_path):
    pass
