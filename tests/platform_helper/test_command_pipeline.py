from unittest.mock import Mock
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_platform_helper.commands.pipeline import generate
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from tests.platform_helper.conftest import EXPECTED_FILES_DIR
from tests.platform_helper.conftest import FIXTURES_DIR
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


def setup_fixtures(fakefs, pipelines_file=f"pipeline/{PLATFORM_CONFIG_FILE}"):
    fakefs.add_real_file(FIXTURES_DIR / pipelines_file, False, PLATFORM_CONFIG_FILE)
    fakefs.add_real_file(FIXTURES_DIR / "valid_workspace.yml", False, "copilot/.workspace")
    fakefs.add_real_directory(EXPECTED_FILES_DIR / "pipeline" / "pipelines", True)
