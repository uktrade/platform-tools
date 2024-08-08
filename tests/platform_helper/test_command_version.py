import re
from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.version import print_desired


@patch("dbt_platform_helper.commands.version.get_desired_platform_helper_version")
def test_calls_versioning_function_and_prints_returned_version(
    mock_get_desired_platform_helper_version,
):
    mock_get_desired_platform_helper_version.return_value = "1.2.3"
    result = CliRunner().invoke(print_desired, [])

    assert len(mock_get_desired_platform_helper_version.mock_calls) == 1
    assert mock_get_desired_platform_helper_version.mock_calls[0].args == (None,)
    assert result.exit_code == 0
    assert re.match(r"\s*1\.2\.3\s*", result.output)


@patch("dbt_platform_helper.commands.version.get_desired_platform_helper_version")
def test_calls_versioning_function_and_prints_returned_version_with_pipeline_override(
    mock_get_desired_platform_helper_version,
):
    mock_get_desired_platform_helper_version.return_value = "1.2.3"
    result = CliRunner().invoke(print_desired, ["--pipeline", "main"])

    assert len(mock_get_desired_platform_helper_version.mock_calls) == 1
    assert mock_get_desired_platform_helper_version.mock_calls[0].args == ("main",)
    assert result.exit_code == 0
    assert re.match(r"\s*1\.2\.3\s*", result.output)
