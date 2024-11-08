from unittest.mock import Mock
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_platform_helper.commands.conduit import conduit


@pytest.mark.parametrize(
    "addon_name",
    [
        ("custom-name-postgres"),
        ("custom-name-rds-postgres"),
        ("custom-name-redis"),
        ("custom-name-opensearch"),
    ],
)
@patch("dbt_platform_helper.commands.conduit.Conduit")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=True),
)
def test_start_conduit(mock_conduit_object, addon_name, mock_application, validate_version):
    """Test that given an app, env and addon name strings, the conduit command
    calls start_conduit with app, env, addon type and addon name."""

    mock_conduit_instance = mock_conduit_object.return_value

    result = CliRunner().invoke(
        conduit,
        [
            addon_name,
            "--app",
            "test-application",
            "--env",
            "development",
        ],
    )

    validate_version.assert_called_once()
    mock_conduit_instance.start.assert_called_once_with(
        mock_application, "development", addon_name, "read"
    )

    assert result.exit_code == 0
