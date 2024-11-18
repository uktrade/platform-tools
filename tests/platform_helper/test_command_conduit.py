from unittest.mock import Mock
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_platform_helper.commands.conduit import conduit
from dbt_platform_helper.exceptions import AddonNotFoundError
from dbt_platform_helper.exceptions import InvalidAddonTypeError
from dbt_platform_helper.exceptions import ParameterNotFoundError
from dbt_platform_helper.providers.copilot import CreateTaskTimeoutError
from dbt_platform_helper.providers.copilot import NoClusterError
from dbt_platform_helper.providers.secrets import SecretNotFoundError


@pytest.mark.parametrize(
    "addon_name",
    [
        "custom-name-postgres",
        "custom-name-rds-postgres",
        "custom-name-redis",
        "custom-name-opensearch",
    ],
)
@patch("dbt_platform_helper.commands.conduit.Conduit")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=True),
)
@patch("dbt_platform_helper.commands.conduit.load_application")
def test_start_conduit(mock_application, mock_conduit_object, addon_name, validate_version):
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

    assert result.exit_code == 0

    validate_version.assert_called_once()
    mock_conduit_instance.start.assert_called_with("development", addon_name, "read")


@pytest.mark.parametrize(
    "exception_type,exception_input_params,expected_message",
    [
        (
            SecretNotFoundError,
            {},
            """No secret called "" for "test-application" in "development" environment.""",
        ),
        (AddonNotFoundError, {}, """Addon "important-db" does not exist."""),
        (
            CreateTaskTimeoutError,
            {},
            """Client (important-db) ECS task has failed to start for "test-application" in "development" environment.""",
        ),
        (
            NoClusterError,
            {},
            """No ECS cluster found for "test-application" in "development" environment.""",
        ),
        (
            ParameterNotFoundError,
            {},
            """No parameter called "/copilot/applications/test-application/environments/development/addons". Try deploying the "test-application" "development" environment.""",
        ),
        (
            InvalidAddonTypeError,
            {"addon_type": "fake-postgres"},
            """Addon type "fake-postgres" is not supported, we support: opensearch, postgres, redis.""",
        ),
    ],
)
@patch("dbt_platform_helper.commands.conduit.Conduit")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=True),
)
@patch("dbt_platform_helper.commands.conduit.load_application")
@patch("click.secho")
def test_start_conduit_exception_is_raised(
    mock_click,
    mock_application,
    mock_conduit_object,
    validate_version,
    exception_type,
    exception_input_params,
    expected_message,
):
    """Test that given an app, env and addon name strings, the conduit command
    calls start_conduit with app, env, addon type and addon name."""

    mock_conduit_instance = mock_conduit_object.return_value
    mock_conduit_instance.start.side_effect = exception_type(**exception_input_params)
    addon_name = "important-db"
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

    mock_click.assert_called_with(expected_message, fg="red")

    assert result.exit_code == 1

    validate_version.assert_called_once()
    mock_conduit_instance.start.assert_called_with("development", addon_name, "read")
