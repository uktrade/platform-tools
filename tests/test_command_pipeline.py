import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

from _pytest.fixtures import fixture
from click.testing import CliRunner

from dbt_copilot_helper.commands.pipeline import generate
from tests.conftest import EXPECTED_FILES_DIR
from tests.conftest import FIXTURES_DIR
from tests.conftest import mock_codestar_connections_boto_client


@patch("boto3.client")
def test_pipeline_generate_with_git_repo_creates_the_pipeline_configuration(
    mocked_boto3_client, tmp_path, switch_to_tmp_dir_and_copy_fixtures
):
    mock_codestar_connections_boto_client(mocked_boto3_client, ["test-app"])
    setup_git_respository()
    buildspec, cfn_patch, manifest = setup_output_file_paths(tmp_path)

    result = CliRunner().invoke(generate)

    assert_output_file_contents_match_expected(buildspec, "buildspec.yml")
    assert_output_file_contents_match_expected(manifest, "manifest.yml")
    assert_output_file_contents_match_expected(cfn_patch, "overrides/cfn.patches.yml")
    assert_file_created_in_stdout(buildspec, result, tmp_path)
    assert_file_created_in_stdout(manifest, result, tmp_path)
    assert_file_created_in_stdout(cfn_patch, result, tmp_path)


@patch("boto3.client")
def test_pipeline_generate_with_no_codestar_connection_exits_with_failure_message(
    mocked_boto3_client, switch_to_tmp_dir_and_copy_fixtures
):
    mock_codestar_connections_boto_client(mocked_boto3_client, [])
    setup_git_respository()

    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert "Error: There is no CodeStar Connection to use" in result.output


def test_pipeline_generate_with_no_repo_fails_with_a_message(switch_to_tmp_dir_and_copy_fixtures):
    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert "Error: The current directory is not a git repository" in result.output


def test_pipeline_generate_with_no_pipeline_yml_fails_with_message(
    switch_to_tmp_dir_and_copy_fixtures,
):
    os.remove("pipelines.yml")

    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert "Error: There is no pipelines.yml" in result.output


def test_pipeline_generate_pipeline_yml_invalid_fails_with_message(
    switch_to_tmp_dir_and_copy_fixtures,
):
    with open("pipelines.yml", "w") as fh:
        print("{invalid data", file=fh)

    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert "Error: The pipelines.yml file is invalid" in result.output


def test_pipeline_generate_bootstrap_yml_invalid_fails_with_message(tmp_path):
    pass


def assert_file_created_in_stdout(output_file, result, tmp_path):
    assert f"File {output_file.relative_to(tmp_path)} created" in result.stdout


def assert_output_file_contents_match_expected(output_file, expected_file):
    exp_files_dir = Path(EXPECTED_FILES_DIR) / "pipeline" / "pipelines" / "test-app-environments"
    assert output_file.read_text().rstrip() == (exp_files_dir / expected_file).read_text().rstrip()


def setup_output_file_paths(tmp_path):
    output_dir = tmp_path / "copilot/pipelines/test-app-environments"
    buildspec = output_dir / "buildspec.yml"
    manifest = output_dir / "manifest.yml"
    cfn_patch = output_dir / "overrides" / "cfn.patches.yml"
    return buildspec, cfn_patch, manifest


def setup_git_respository():
    subprocess.run(["git", "init"])
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:uktrade/test-app.git"])


@fixture
def switch_to_tmp_dir_and_copy_fixtures(tmp_path):
    os.chdir(tmp_path)
    shutil.copy(FIXTURES_DIR / "valid_bootstrap_config.yml", "bootstrap.yml")
    shutil.copy(FIXTURES_DIR / "pipeline/pipelines.yml", "pipelines.yml")

    return tmp_path
