from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.version import get_platform_helper_for_project


class TestVersionCommand:
    @patch("dbt_platform_helper.commands.version.PlatformHelperVersioning.get_default_version")
    def test_calls_versioning_function(
        self,
        mock_required_version,
    ):

        result = CliRunner().invoke(get_platform_helper_for_project, [])

        assert result.exit_code == 0
        mock_required_version.assert_called_once()
