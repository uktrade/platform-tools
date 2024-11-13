import re
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_platform_helper.commands.version import VersionCommand


@pytest.mark.usefixtures("create_valid_platform_config_file")
class TestVersionCommandWithValidConfig:
    @patch("dbt_platform_helper.commands.version.get_required_platform_helper_version")
    def test_calls_versioning_function_and_prints_returned_version(
        self,
        mock_get_required_platform_helper_version,
    ):
        mock_get_required_platform_helper_version.return_value = "1.2.3"

        command = VersionCommand().command
        result = CliRunner().invoke(command, [])

        assert len(mock_get_required_platform_helper_version.mock_calls) == 1
        assert mock_get_required_platform_helper_version.mock_calls[0].args == (None,)
        assert result.exit_code == 0
        assert re.match(r"\s*1\.2\.3\s*", result.output)

    @patch("dbt_platform_helper.commands.version.get_required_platform_helper_version")
    def test_calls_versioning_function_and_prints_returned_version_with_pipeline_override(
        self,
        mock_get_required_platform_helper_version,
    ):
        mock_get_required_platform_helper_version.return_value = "1.2.3"

        command = VersionCommand().command
        result = CliRunner().invoke(command, ["--pipeline", "main"])

        assert len(mock_get_required_platform_helper_version.mock_calls) == 1
        assert mock_get_required_platform_helper_version.mock_calls[0].args == ("main",)
        assert result.exit_code == 0
        assert re.match(r"\s*1\.2\.3\s*", result.output)

    def test_fall_back_on_default_if_pipeline_option_is_not_a_valid_pipeline(self):
        command = VersionCommand().command
        result = CliRunner().invoke(command, ["--pipeline", "bogus"])

        assert result.exit_code == 0
        assert result.output == "10.2.0\n"


@pytest.mark.usefixtures("create_invalid_platform_config_file")
@patch("dbt_platform_helper.utils.versioning._get_latest_release", return_value="10.9.9")
class TestVersionCommandWithInvalidConfig:
    def test_works_given_invalid_config(self, mock_latest_release):
        command = VersionCommand().command
        result = CliRunner().invoke(command, [])

        assert result.exit_code == 0
        assert result.output == "1.2.3\n"

    def test_pipeline_override_given_invalid_config(self, mock_latest_release):
        command = VersionCommand().command
        result = CliRunner().invoke(command, ["--pipeline", "prod-main"])

        assert result.exit_code == 0
        assert result.output == "9.0.9\n"
