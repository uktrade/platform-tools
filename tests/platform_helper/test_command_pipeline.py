import os
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner
from freezegun.api import freeze_time

from dbt_platform_helper.commands.pipeline import generate
from dbt_platform_helper.constants import CODEBASE_PIPELINES_KEY
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from tests.platform_helper.conftest import EXPECTED_FILES_DIR
from tests.platform_helper.conftest import FIXTURES_DIR
from tests.platform_helper.conftest import assert_file_created_in_stdout
from tests.platform_helper.conftest import mock_codestar_connections_boto_client


@pytest.mark.parametrize(
    "cli_args,expected_pipeline_args",
    [
        ([], [None, None]),
        (
            ["--terraform-platform-modules-version", "1.2.3", "--deploy-branch", "my-branch"],
            ["1.2.3", "my-branch"],
        ),
        (["--terraform-platform-modules-version", "1.2.3"], ["1.2.3", None]),
        (["--deploy-branch", "my-branch"], [None, "my-branch"]),
        (
            ["--terraform-platform-modules-version", "1.2.3", "--deploy-branch", "my-branch"],
            ["1.2.3", "my-branch"],
        ),
    ],
)
@patch("dbt_platform_helper.commands.pipeline.Pipelines", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_passes_args_to_pipelines_instance(
    mock_pipelines, cli_args, expected_pipeline_args
):
    mock_pipeline_instance = Mock()
    mock_pipelines.return_value = mock_pipeline_instance

    CliRunner().invoke(generate, cli_args)

    mock_pipeline_instance.generate.assert_called_once_with(*expected_pipeline_args)


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_with_git_repo_creates_the_pipeline_configuration(
    git_remote, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(fakefs)

    result = CliRunner().invoke(generate)

    expected_files_dir = Path(EXPECTED_FILES_DIR) / "pipeline" / "pipelines"

    # Codebases
    output_files = setup_output_file_paths_for_codebases()
    assert_yaml_in_output_file_matches_expected(
        output_files[0], expected_files_dir / "application" / "manifest.yml"
    )
    assert_yaml_in_output_file_matches_expected(
        output_files[3], expected_files_dir / "application" / "overrides/buildspec.deploy.yml"
    )
    assert_yaml_in_output_file_matches_expected(
        output_files[4], expected_files_dir / "application" / "overrides/buildspec.image.yml"
    )
    for file in output_files:
        assert_file_created_in_stdout(file, result)


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
@patch("dbt_platform_helper.domain.pipelines.get_account_details")
@patch("dbt_platform_helper.domain.pipelines.get_public_repository_arn")
def test_pipeline_generate_with_additional_ecr_repo_adds_public_ecr_perms(
    get_public_repository_arn,
    get_account_details,
    git_remote,
    mock_aws_session,
    fakefs,
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    get_account_details.return_value = "000000000000", "abc1234"
    get_public_repository_arn.return_value = (
        "arn:aws:ecr-public::000000000000:repository/test-app/application"
    )
    setup_fixtures(fakefs, pipelines_file="pipeline/platform-config-with-public-repo.yml")

    result = CliRunner().invoke(generate)

    expected_files_dir = Path(EXPECTED_FILES_DIR) / "pipeline" / "pipelines"
    # Codebases
    output_files = setup_output_file_paths_for_codebases()
    assert_yaml_in_output_file_matches_expected(
        output_files[0], expected_files_dir / "application" / "manifest-public-repo.yml"
    )
    assert_yaml_in_output_file_matches_expected(
        output_files[3], expected_files_dir / "application" / "overrides/buildspec.deploy.yml"
    )
    assert_yaml_in_output_file_matches_expected(
        output_files[4], expected_files_dir / "application" / "overrides/buildspec.image.yml"
    )
    for file in output_files:
        assert_file_created_in_stdout(file, result)


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_with_only_environments_creates_the_pipeline_configuration(
    git_remote, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(fakefs)
    pipelines = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    del pipelines[CODEBASE_PIPELINES_KEY]
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(pipelines))

    CliRunner().invoke(generate)

    assert_codebase_pipeline_config_was_not_generated()


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_with_wildcarded_branch_creates_the_pipeline_configuration(
    git_remote, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(fakefs, pipelines_file="pipeline/platform-config-with-valid-wildcard-branch.yml")
    pipelines = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(pipelines))

    result = CliRunner().invoke(generate)

    assert result.exit_code == 0
    assert_codebase_pipeline_config_was_generated()


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_with_invalid_wildcarded_branch_does_not_create_the_pipeline_configuration(
    git_remote, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(
        fakefs, pipelines_file="pipeline/platform-config-with-invalid-wildcard-branch.yml"
    )
    pipelines = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(pipelines))

    result = CliRunner().invoke(generate)

    assert result.exit_code != 0
    assert_codebase_pipeline_config_was_not_generated()


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_with_only_codebases_creates_the_pipeline_configuration(
    git_remote, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(fakefs)
    pipelines = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    del pipelines["environments"]
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(pipelines))

    CliRunner().invoke(generate)

    assert_codebase_pipeline_config_was_generated()


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_with_terraform_directory_only_creates_pipeline_configuration(
    git_remote, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(fakefs, pipelines_file="pipeline/platform-config-for-terraform.yml")

    CliRunner().invoke(generate)

    assert_codebase_pipeline_config_was_generated()


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_deletes_any_existing_config_files_and_writes_new_ones(
    git_remote, mock_aws_session, fakefs, fs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(fakefs)
    fs.create_dir("copilot/pipelines")
    fs.create_file("copilot/pipelines/unnecessary_file.yml")
    codebases_files = setup_output_file_paths_for_codebases()

    result = CliRunner().invoke(generate)

    for file in codebases_files:
        assert_file_created_in_stdout(file, result)

    result = CliRunner().invoke(generate)

    assert "Deleting copilot/pipelines directory." in result.stdout

    for file in codebases_files:
        assert_file_created_in_stdout(file, result)

    assert not os.path.exists("copilot/pipelines/unnecessary_file.yml")


@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_with_no_codestar_connection_exits_with_message(
    git_remote, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, [])
    setup_fixtures(fakefs)

    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert 'Error: There is no CodeStar Connection named "test-app" to use' in result.output


@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value=None)
def test_pipeline_generate_with_no_repo_fails_with_message(git_remote, fakefs):
    setup_fixtures(fakefs)
    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert "Error: The current directory is not a git repository" in result.output


def test_pipeline_generate_pipeline_yml_defining_the_same_env_twice_fails_with_message(fakefs):
    setup_fixtures(fakefs)
    pipelines = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    pipelines_section = pipelines[CODEBASE_PIPELINES_KEY][0]["pipelines"]
    pipelines_section[1]["environments"] = [{"name": "dev"}] + pipelines_section[1]["environments"]
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(pipelines))

    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert (
        f"Error: The {PLATFORM_CONFIG_FILE} file is invalid, each environment can only be listed in a "
        "single pipeline"
    ) in result.output


def test_pipeline_generate_with_no_workspace_file_fails_with_message(fakefs):
    setup_fixtures(fakefs)
    os.remove("copilot/.workspace")

    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert "Cannot get application name. No copilot/.workspace file found" in result.output


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_without_accounts_creates_the_pipeline_configuration(
    git_remote, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(fakefs)
    pipelines = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    del pipelines["accounts"]
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(pipelines))

    CliRunner().invoke(generate)

    assert_codebase_pipeline_config_was_generated()


def assert_yaml_in_output_file_matches_expected(output_file, expected_file):
    def get_yaml(content):
        return yaml.safe_load(content)

    actual_content = output_file.read_text()
    expected_content = expected_file.read_text()

    assert actual_content.partition("\n")[0].strip() == expected_content.partition("\n")[0].strip()
    assert get_yaml(actual_content) == get_yaml(expected_content)


def assert_codebase_pipeline_config_was_generated():
    for file in setup_output_file_paths_for_codebases():
        assert Path(file).exists(), f"File {file} should exist"


def assert_codebase_pipeline_config_was_not_generated():
    for file in setup_output_file_paths_for_codebases():
        assert not Path(file).exists(), f"File {file} should not exist"


def setup_output_file_paths_for_codebases():
    output_dir = Path("copilot/pipelines/application")
    overrides_dir = output_dir / "overrides"

    return (
        output_dir / "manifest.yml",
        overrides_dir / "bin" / "override.ts",
        overrides_dir / ".gitignore",
        overrides_dir / "buildspec.deploy.yml",
        overrides_dir / "buildspec.image.yml",
        overrides_dir / "cdk.json",
        overrides_dir / "package-lock.json",
        overrides_dir / "package.json",
        overrides_dir / "stack.ts",
        overrides_dir / "tsconfig.json",
        overrides_dir / "types.ts",
    )


def setup_fixtures(fakefs, pipelines_file=f"pipeline/{PLATFORM_CONFIG_FILE}"):
    fakefs.add_real_file(FIXTURES_DIR / pipelines_file, False, PLATFORM_CONFIG_FILE)
    fakefs.add_real_file(FIXTURES_DIR / "valid_workspace.yml", False, "copilot/.workspace")
    fakefs.add_real_directory(EXPECTED_FILES_DIR / "pipeline" / "pipelines", True)
