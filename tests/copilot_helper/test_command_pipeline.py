import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import yaml
from _pytest.fixtures import fixture
from click.testing import CliRunner
from freezegun.api import freeze_time

from dbt_copilot_helper.commands.pipeline import generate
from tests.copilot_helper.conftest import EXPECTED_FILES_DIR
from tests.copilot_helper.conftest import FIXTURES_DIR
from tests.copilot_helper.conftest import assert_file_created_in_stdout
from tests.copilot_helper.conftest import assert_file_overwritten_in_stdout
from tests.copilot_helper.conftest import mock_codestar_connections_boto_client


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("boto3.client")
def test_pipeline_generate_with_git_repo_creates_the_pipeline_configuration(
    mocked_boto3_client, tmp_path, switch_to_tmp_dir_and_copy_fixtures
):
    mock_codestar_connections_boto_client(mocked_boto3_client, ["test-app"])
    setup_git_repository()
    buildspec, cfn_patch, manifest = setup_output_file_paths_for_environments(tmp_path)

    result = CliRunner().invoke(generate)

    expected_files_dir = Path(EXPECTED_FILES_DIR) / "pipeline" / "pipelines"
    # Environments
    assert_yaml_in_output_file_matches_expected(
        buildspec, expected_files_dir / "environments" / "buildspec.yml"
    )
    assert_yaml_in_output_file_matches_expected(
        manifest, expected_files_dir / "environments" / "manifest.yml"
    )
    assert_yaml_in_output_file_matches_expected(
        cfn_patch, expected_files_dir / "environments" / "overrides/cfn.patches.yml"
    )
    assert_file_created_in_stdout(buildspec, result, tmp_path)
    assert_file_created_in_stdout(manifest, result, tmp_path)
    assert_file_created_in_stdout(cfn_patch, result, tmp_path)

    # Codebases
    output_files = setup_output_file_paths_for_codebases(tmp_path)
    assert_yaml_in_output_file_matches_expected(
        output_files[0], expected_files_dir / "application" / "manifest.yml"
    )

    for file in output_files:
        assert_file_created_in_stdout(file, result, tmp_path)


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("boto3.client")
def test_pipeline_generate_with_only_environments_creates_the_pipeline_configuration(
    mocked_boto3_client, tmp_path, switch_to_tmp_dir_and_copy_fixtures
):
    mock_codestar_connections_boto_client(mocked_boto3_client, ["test-app"])
    setup_git_repository()

    pipelines = yaml.safe_load(Path("pipelines.yml").read_text())
    del pipelines["codebases"]
    Path("pipelines.yml").write_text(yaml.dump(pipelines))

    CliRunner().invoke(generate)

    environments_files = setup_output_file_paths_for_environments(tmp_path)
    for file in environments_files:
        assert Path(file).exists()

    codebase_files = setup_output_file_paths_for_codebases(tmp_path)
    for file in codebase_files:
        assert not Path(file).exists()


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("boto3.client")
def test_pipeline_generate_with_only_codebases_creates_the_pipeline_configuration(
    mocked_boto3_client, tmp_path, switch_to_tmp_dir_and_copy_fixtures
):
    mock_codestar_connections_boto_client(mocked_boto3_client, ["test-app"])
    setup_git_repository()

    pipelines = yaml.safe_load(Path("pipelines.yml").read_text())
    del pipelines["environments"]
    Path("pipelines.yml").write_text(yaml.dump(pipelines))

    CliRunner().invoke(generate)

    environments_files = setup_output_file_paths_for_environments(tmp_path)
    for file in environments_files:
        assert not Path(file).exists()

    codebase_files = setup_output_file_paths_for_codebases(tmp_path)
    for file in codebase_files:
        assert Path(file).exists()


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("boto3.client")
def test_pipeline_generate_with_empty_pipelines_yml_does_nothing(
    mocked_boto3_client, tmp_path, switch_to_tmp_dir_and_copy_fixtures
):
    Path("pipelines.yml").write_text(yaml.dump({}))

    result = CliRunner().invoke(generate)

    assert "Error: No environment or codebase pipelines defined in pipelines.yml" in result.output


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("boto3.client")
def test_pipeline_generate_overwrites_any_existing_config_files(
    mocked_boto3_client, tmp_path, switch_to_tmp_dir_and_copy_fixtures
):
    mock_codestar_connections_boto_client(mocked_boto3_client, ["test-app"])
    setup_git_repository()
    environments_files = setup_output_file_paths_for_environments(tmp_path)
    codebases_files = setup_output_file_paths_for_codebases(tmp_path)

    result = CliRunner().invoke(generate)
    for file in environments_files + codebases_files:
        assert_file_created_in_stdout(file, result, tmp_path)

    result = CliRunner().invoke(generate)

    for file in environments_files + codebases_files:
        assert_file_overwritten_in_stdout(file, result, tmp_path)


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("boto3.client")
def test_pipeline_generate_with_no_bootstrap_yml_succeeds(
    mocked_boto3_client,
    switch_to_tmp_dir_and_copy_fixtures,
):
    os.remove("bootstrap.yml")
    setup_git_repository()
    mock_codestar_connections_boto_client(mocked_boto3_client, ["test-app"])

    result = CliRunner().invoke(generate)

    assert result.exit_code == 0


@patch("boto3.client")
def test_pipeline_generate_with_no_codestar_connection_exits_with_message(
    mocked_boto3_client, switch_to_tmp_dir_and_copy_fixtures
):
    mock_codestar_connections_boto_client(mocked_boto3_client, [])
    setup_git_repository()

    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert "Error: There is no CodeStar Connection to use" in result.output


def test_pipeline_generate_with_no_repo_fails_with_message(switch_to_tmp_dir_and_copy_fixtures):
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


def test_pipeline_generate_pipeline_yml_defining_the_same_env_twice_fails_with_message(
    switch_to_tmp_dir_and_copy_fixtures,
):
    pipelines = yaml.safe_load(Path("pipelines.yml").read_text())
    pipelines["codebases"][0]["pipelines"][1]["environments"] = [{"name": "dev"}] + pipelines[
        "codebases"
    ][0]["pipelines"][1]["environments"]
    Path("pipelines.yml").write_text(yaml.dump(pipelines))

    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert (
        "Error: The pipelines.yml file is invalid, each environment can only be listed in a "
        "single pipeline"
    ) in result.output


def test_pipeline_generate_with_no_bootstrap_yml_or_workspace_fails_with_message(
    switch_to_tmp_dir_and_copy_fixtures,
):
    os.remove("bootstrap.yml")
    os.remove("copilot/.workspace")

    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert "Error: No valid bootstrap.yml or copilot/.workspace file found" in result.output


def test_pipeline_generate_with_invalid_bootstrap_yml_and_no_workspace_fails_with_message(
    switch_to_tmp_dir_and_copy_fixtures,
):
    with open("bootstrap.yml", "w") as fh:
        print("{invalid data", file=fh)
    os.remove("copilot/.workspace")

    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert "Error: No valid bootstrap.yml or copilot/.workspace file found" in result.output


def assert_yaml_in_output_file_matches_expected(output_file, expected_file):
    def get_yaml(content):
        return yaml.safe_load(content)

    actual_content = output_file.read_text()
    expected_content = expected_file.read_text()

    assert actual_content.partition("\n")[0].strip() == expected_content.partition("\n")[0].strip()
    assert get_yaml(actual_content) == get_yaml(expected_content)


def setup_output_file_paths_for_environments(tmp_path):
    output_dir = tmp_path / "copilot/pipelines/environments"
    buildspec = output_dir / "buildspec.yml"
    manifest = output_dir / "manifest.yml"
    cfn_patch = output_dir / "overrides" / "cfn.patches.yml"
    return buildspec, cfn_patch, manifest


def setup_output_file_paths_for_codebases(tmp_path):
    output_dir = tmp_path / "copilot/pipelines/application"
    overrides_dir = output_dir / "overrides"

    manifest = output_dir / "manifest.yml"
    override = overrides_dir / "bin" / "override.ts"
    gitignore = overrides_dir / ".gitignore"
    buildspec_deploy = overrides_dir / "buildspec.deploy.yml"
    buildspec_image = overrides_dir / "buildspec.image.yml"
    cdk_json = overrides_dir / "cdk.json"
    package_lock = overrides_dir / "package-lock.json"
    package = overrides_dir / "package.json"
    stack = overrides_dir / "stack.ts"
    tsconfig = overrides_dir / "tsconfig.json"
    types = overrides_dir / "types.ts"

    return (
        manifest,
        override,
        gitignore,
        buildspec_deploy,
        buildspec_image,
        cdk_json,
        package_lock,
        package,
        stack,
        tsconfig,
        types,
    )


def setup_git_repository():
    subprocess.run(["git", "init", "--initial-branch", "main"], stdout=subprocess.PIPE)
    subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:uktrade/test-app-deploy.git"],
        stdout=subprocess.PIPE,
    )


@fixture
def switch_to_tmp_dir_and_copy_fixtures(tmp_path):
    os.chdir(tmp_path)
    shutil.copy(FIXTURES_DIR / "valid_bootstrap_config.yml", "bootstrap.yml")
    os.mkdir("copilot")
    shutil.copy(FIXTURES_DIR / "valid_workspace.yml", "copilot/.workspace")
    shutil.copy(FIXTURES_DIR / "pipeline/pipelines.yml", "pipelines.yml")

    return tmp_path
