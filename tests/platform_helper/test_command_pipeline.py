import os
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner
from freezegun.api import freeze_time

from dbt_platform_helper.commands.pipeline import CODEBASE_PIPELINES_KEY
from dbt_platform_helper.commands.pipeline import (
    _determine_terraform_platform_modules_version,
)
from dbt_platform_helper.commands.pipeline import generate
from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from tests.platform_helper.conftest import EXPECTED_FILES_DIR
from tests.platform_helper.conftest import FIXTURES_DIR
from tests.platform_helper.conftest import assert_file_created_in_stdout
from tests.platform_helper.conftest import mock_codestar_connections_boto_client


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_with_git_repo_creates_the_pipeline_configuration(
    git_remote, get_aws_session_or_abort, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(fakefs)
    buildspec, cfn_patch, manifest = setup_output_file_paths_for_environments()

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
    assert_file_created_in_stdout(buildspec, result)
    assert_file_created_in_stdout(manifest, result)
    assert_file_created_in_stdout(cfn_patch, result)
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
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
@patch("dbt_platform_helper.commands.pipeline.get_account_details")
@patch("dbt_platform_helper.commands.pipeline.get_public_repository_arn")
def test_pipeline_generate_with_additional_ecr_repo_adds_public_ecr_perms(
    get_public_repository_arn,
    get_account_details,
    git_remote,
    get_aws_session_or_abort,
    mock_aws_session,
    fakefs,
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    get_account_details.return_value = "000000000000", "abc1234"
    get_public_repository_arn.return_value = (
        "arn:aws:ecr-public::000000000000:repository/test-app/application"
    )
    setup_fixtures(fakefs, pipelines_file="pipeline/platform-config-with-public-repo.yml")
    buildspec, cfn_patch, manifest = setup_output_file_paths_for_environments()

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
    assert_file_created_in_stdout(buildspec, result)
    assert_file_created_in_stdout(manifest, result)
    assert_file_created_in_stdout(cfn_patch, result)
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
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_with_only_environments_creates_the_pipeline_configuration(
    git_remote, get_aws_session_or_abort, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(fakefs)
    pipelines = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    del pipelines[CODEBASE_PIPELINES_KEY]
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(pipelines))

    CliRunner().invoke(generate)

    assert_environment_pipeline_config_was_generated()
    assert_codebase_pipeline_config_was_not_generated()


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_with_wildcarded_branch_creates_the_pipeline_configuration(
    git_remote, get_aws_session_or_abort, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(fakefs, pipelines_file="pipeline/platform-config-with-valid-wildcard-branch.yml")
    pipelines = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(pipelines))

    result = CliRunner().invoke(generate)

    assert result.exit_code == 0
    assert_environment_pipeline_config_was_generated()
    assert_codebase_pipeline_config_was_generated()


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_with_invalid_wildcarded_branch_does_not_create_the_pipeline_configuration(
    git_remote, get_aws_session_or_abort, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(
        fakefs, pipelines_file="pipeline/platform-config-with-invalid-wildcard-branch.yml"
    )
    pipelines = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(pipelines))

    result = CliRunner().invoke(generate)

    assert result.exit_code != 0
    assert_environment_pipeline_config_was_not_generated()
    assert_codebase_pipeline_config_was_not_generated()


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_with_only_codebases_creates_the_pipeline_configuration(
    git_remote, get_aws_session_or_abort, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(fakefs)
    pipelines = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    del pipelines["environments"]
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(pipelines))

    CliRunner().invoke(generate)

    assert_environment_pipeline_config_was_not_generated()
    assert_codebase_pipeline_config_was_generated()


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_with_terraform_directory_only_creates_pipeline_configuration(
    git_remote, get_aws_session_or_abort, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(fakefs, pipelines_file="pipeline/platform-config-for-terraform.yml")

    CliRunner().invoke(generate)

    assert_environment_pipeline_config_was_not_generated()
    assert_codebase_pipeline_config_was_generated()


@patch("dbt_platform_helper.commands.pipeline.load_and_validate_platform_config")
def test_pipeline_generate_with_empty_platform_config_yml_outputs_warning(get_aws_session_or_abort):
    get_aws_session_or_abort.returns({"application": "my-app"})

    result = CliRunner().invoke(generate)

    assert "No pipelines defined: nothing to do." in result.output


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_deletes_any_existing_config_files_and_writes_new_ones(
    git_remote, get_aws_session_or_abort, mock_aws_session, fakefs, fs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(fakefs)
    fs.create_dir("copilot/pipelines")
    fs.create_file("copilot/pipelines/unnecessary_file.yml")
    environments_files = setup_output_file_paths_for_environments()
    codebases_files = setup_output_file_paths_for_codebases()

    result = CliRunner().invoke(generate)

    for file in environments_files + codebases_files:
        assert_file_created_in_stdout(file, result)

    result = CliRunner().invoke(generate)

    assert "Deleting copilot/pipelines directory." in result.stdout

    for file in environments_files + codebases_files:
        assert_file_created_in_stdout(file, result)

    assert not os.path.exists("copilot/pipelines/unnecessary_file.yml")


@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_with_no_codestar_connection_exits_with_message(
    git_remote, get_aws_session_or_abort, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, [])
    setup_fixtures(fakefs)

    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert 'Error: There is no CodeStar Connection named "test-app" to use' in result.output


@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value=None)
def test_pipeline_generate_with_no_repo_fails_with_message(
    git_remote, get_aws_session_or_abort, fakefs
):
    setup_fixtures(fakefs)
    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert "Error: The current directory is not a git repository" in result.output


def test_pipeline_generate_with_no_pipeline_yml_fails_with_message(fakefs):
    setup_fixtures(fakefs)
    os.remove(PLATFORM_CONFIG_FILE)

    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert (
        f"`{PLATFORM_CONFIG_FILE}` is missing. Please check it exists and you are in the root directory of your deployment project."
        in result.output
    )


def test_pipeline_generate_pipeline_yml_invalid_fails_with_message(fakefs):
    setup_fixtures(fakefs)
    Path(PLATFORM_CONFIG_FILE).write_text("{invalid data")

    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    message = result.output
    assert f"Error: {PLATFORM_CONFIG_FILE} is not valid YAML" in message


@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
def test_pipeline_generate_pipeline_yml_defining_the_same_env_twice_fails_with_message(
    get_aws_session_or_abort, fakefs
):
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


@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
def test_pipeline_generate_with_no_workspace_file_fails_with_message(
    get_aws_session_or_abort, fakefs
):
    setup_fixtures(fakefs)
    os.remove("copilot/.workspace")

    result = CliRunner().invoke(generate)

    assert result.exit_code == 1
    assert "Cannot get application name. No copilot/.workspace file found" in result.output


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_pipeline_generate_without_accounts_creates_the_pipeline_configuration(
    git_remote, get_aws_command_or_abort, mock_aws_session, fakefs
):
    mock_codestar_connections_boto_client(mock_aws_session, ["test-app"])
    setup_fixtures(fakefs)
    pipelines = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    del pipelines["accounts"]
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(pipelines))

    CliRunner().invoke(generate)

    assert_environment_pipeline_config_was_generated()
    assert_codebase_pipeline_config_was_generated()


def assert_terraform(app_name, aws_account, expected_version, expected_branch):
    expected_files_dir = Path(f"terraform/environment-pipelines/{aws_account}/main.tf")
    assert expected_files_dir.exists()
    content = expected_files_dir.read_text()
    print(content)

    assert "# WARNING: This is an autogenerated file, not for manual editing." in content
    assert "# Generated by platform-helper v0.1-TEST / 2024-10-28 12:00:00" in content
    assert f'profile                  = "{aws_account}"' in content
    assert (
        f"git::https://github.com/uktrade/terraform-platform-modules.git//environment-pipelines?depth=1&ref={expected_version}"
        in content
    )
    assert f'application         = "{app_name}"' in content
    expected_branch_value = expected_branch if expected_branch else "each.value.branch"
    assert f"branch              = {expected_branch_value} in content"


@freeze_time("2024-10-28 12:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
@pytest.mark.parametrize(
    "cli_terraform_platform_version, config_terraform_platform_version, expected_terraform_platform_version, cli_demodjango_branch, expected_demodjango_branch",
    [  # config_terraform_platform_version sets the platform-config.yml to include the TPM version at platform-config.yml/default_versions/terraform-platform-modules
        ("7", True, "7", None, None),  # Case with cli_terraform_platform_version
        (
            None,
            True,
            "4.0.0",
            "demodjango-branch",
            "demodjango-branch",
        ),  # Case with config_terraform_platform_version and specific branch
        (None, True, "4.0.0", None, None),  # Case with config_terraform_platform_version
        (None, None, "5", None, None),  # Case with default TPM version and without branch, defaults
    ],
)
def test_generate_pipeline_command_generate_terraform_files_for_environment_pipeline_manifest(
    git_remote,
    get_aws_command_or_abort,
    mock_aws_session,
    fakefs,
    cli_terraform_platform_version,
    config_terraform_platform_version,
    expected_terraform_platform_version,
    cli_demodjango_branch,
    expected_demodjango_branch,
):

    app_name = "test-app"
    mock_codestar_connections_boto_client(mock_aws_session, [app_name])

    if config_terraform_platform_version:
        setup_fixtures(
            fakefs,
            pipelines_file="pipeline/platform-config-for-terraform-environment-pipelines-with-tpm-version.yml",
        )
    else:
        setup_fixtures(
            fakefs,
            pipelines_file="pipeline/platform-config-for-terraform-environment-pipelines.yml",
        )

    args = []
    if cli_terraform_platform_version:
        args.extend(["--terraform-platform-modules-version", cli_terraform_platform_version])
    if cli_demodjango_branch:
        args.extend(["--deploy-branch", cli_demodjango_branch])

    CliRunner().invoke(generate, args=args)

    assert_terraform(
        app_name,
        "platform-sandbox-test",
        expected_terraform_platform_version,
        expected_demodjango_branch,
    )
    assert_terraform(
        app_name,
        "platform-prod-test",
        expected_terraform_platform_version,
        expected_demodjango_branch,
    )


@freeze_time("2024-10-28 12:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
def test_generate_pipeline_command_doesnt_generate_terraform_files_if_legacy_project(
    git_remote,
    get_aws_command_or_abort,
    mock_aws_session,
    fakefs,
):
    app_name = "test-app"
    mock_codestar_connections_boto_client(mock_aws_session, [app_name])
    setup_fixtures(fakefs, pipelines_file="pipeline/platform-config-legacy-project.yml")
    CliRunner().invoke(generate, args=[])

    for aws_account in ["platform-sandbox-test", "platform-prod-test"]:
        expected_files_dir = Path(f"terraform/environment-pipelines/{aws_account}/main.tf")
        assert not expected_files_dir.exists()


@pytest.mark.parametrize(
    "cli_terraform_platform_version, config_terraform_platform_version, expected_version",
    [
        ("feature_branch", "5", "feature_branch"),
        (None, "5", "5"),
        (None, None, DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION),
    ],
)
def test_determine_terraform_platform_modules_version(
    cli_terraform_platform_version, config_terraform_platform_version, expected_version
):
    assert (
        _determine_terraform_platform_modules_version(
            cli_terraform_platform_version, config_terraform_platform_version
        )
        == expected_version
    )


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


def assert_environment_pipeline_config_was_generated():
    for file in setup_output_file_paths_for_environments():
        assert Path(file).exists(), f"File {file} should exist"


def assert_environment_pipeline_config_was_not_generated():
    for file in setup_output_file_paths_for_environments():
        assert not Path(file).exists(), f"File {file} should not exist"


def setup_output_file_paths_for_environments():
    output_dir = Path("./copilot/pipelines/environments")
    buildspec = output_dir / "buildspec.yml"
    manifest = output_dir / "manifest.yml"
    cfn_patch = output_dir / "overrides" / "cfn.patches.yml"
    return buildspec, cfn_patch, manifest


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
