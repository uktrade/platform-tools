from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_platform_helper.commands.version import version


@pytest.mark.usefixtures("create_valid_platform_config_file")
class TestVersionCommandWithValidConfig:
    @patch(
        "dbt_platform_helper.commands.version.RequiredVersion.get_required_platform_helper_version"
    )
    @patch("click.secho")
    def test_calls_versioning_function_and_prints_returned_version(
        self,
        mock_click,
        mock_required_version,
    ):
        mock_required_version.return_value = "1.2.3"

        result = CliRunner().invoke(version, [])

        mock_required_version.assert_called_with(None)
        mock_click.assert_called_with("1.2.3")
        assert result.exit_code == 0

    @patch(
        "dbt_platform_helper.commands.version.RequiredVersion.get_required_platform_helper_version"
    )
    @patch("click.secho")
    def test_calls_versioning_function_and_prints_returned_version_with_pipeline_override(
        self,
        mock_click,
        mock_required_version,
    ):
        mock_required_version.return_value = "1.2.3"

        result = CliRunner().invoke(version, ["--pipeline", "main"])

        mock_required_version.assert_called_with("main")
        mock_click.assert_called_with("1.2.3")
        assert result.exit_code == 0


# TODO: MOVE INTO DOMAIN TESTS
@pytest.mark.usefixtures("create_invalid_platform_config_file")
@patch("dbt_platform_helper.utils.versioning._get_latest_release", return_value="10.9.9")
class TestVersionCommandWithInvalidConfig:
    def test_works_given_invalid_config(self, mock_latest_release):
        result = CliRunner().invoke(version, [])

        assert result.exit_code == 0
        assert result.output == "1.2.3\n"

    def test_pipeline_override_given_invalid_config(self, mock_latest_release):
        result = CliRunner().invoke(version, ["--pipeline", "prod-main"])

        assert result.exit_code == 0
        assert result.output == "9.0.9\n"
