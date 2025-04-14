from unittest.mock import Mock
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_platform_helper.commands.pipeline import generate
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from tests.platform_helper.conftest import EXPECTED_FILES_DIR
from tests.platform_helper.conftest import FIXTURES_DIR


@pytest.mark.parametrize(
    "cli_args, expected_pipeline_args",
    [
        ([], [None]),
        (["--deploy-branch", "my-branch"], ["my-branch"]),
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


@patch(
    "dbt_platform_helper.commands.pipeline.Pipelines", side_effect=Exception("Something went wrong")
)
def test_pipeline_generate_exceptions_are_handled(mock_pipelines):
    result = CliRunner().invoke(generate, [])
    assert result.exit_code == 1

    assert "Error: Something went wrong" in result.output


def setup_fixtures(fakefs, pipelines_file=f"pipeline/{PLATFORM_CONFIG_FILE}"):
    fakefs.add_real_file(FIXTURES_DIR / pipelines_file, False, PLATFORM_CONFIG_FILE)
    fakefs.add_real_file(FIXTURES_DIR / "valid_workspace.yml", False, "copilot/.workspace")
    fakefs.add_real_directory(EXPECTED_FILES_DIR / "pipeline" / "pipelines", True)
