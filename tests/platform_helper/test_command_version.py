from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.version import version
from dbt_platform_helper.platform_exception import PlatformException


class TestVersionCommand:
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

        assert result.exit_code == 0
        mock_required_version.assert_called_with(None)
        mock_click.assert_called_with("1.2.3")

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

        assert result.exit_code == 0
        mock_required_version.assert_called_with("main")
        mock_click.assert_called_with("1.2.3")

    @patch(
        "dbt_platform_helper.commands.version.RequiredVersion.get_required_platform_helper_version"
    )
    @patch("click.secho")
    def test_prints_error_message_if_exception_is_thrown_by_get_required_platform_helper_version(
        self,
        mock_click,
        mock_required_version,
    ):
        mock_required_version.side_effect = PlatformException("Something bad happened")

        result = CliRunner().invoke(version, ["--pipeline", "main"])

        assert result.exit_code == 1
        mock_click.assert_called_with("Error: Something bad happened", err=True, fg="red")
