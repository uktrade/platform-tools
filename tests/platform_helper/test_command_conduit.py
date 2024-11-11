from unittest.mock import Mock
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_platform_helper.commands.conduit import conduit
from dbt_platform_helper.providers.aws import SecretNotFoundError
from dbt_platform_helper.providers.copilot import AddonNotFoundError
from dbt_platform_helper.providers.copilot import CreateTaskTimeoutError
from dbt_platform_helper.providers.copilot import InvalidAddonTypeError
from dbt_platform_helper.providers.copilot import NoClusterError
from dbt_platform_helper.providers.copilot import ParameterNotFoundError


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

    print(result.output)

    assert result.exit_code == 0

    validate_version.assert_called_once()
    mock_conduit_instance.start.assert_called_with("development", addon_name, "read")


@patch("dbt_platform_helper.commands.conduit.Conduit")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=True),
)
@patch("dbt_platform_helper.commands.conduit.load_application")
@patch("click.secho")
def test_start_conduit_exception_secret_not_found(
    mock_click, mock_application, mock_conduit_object, validate_version
):
    """Test that given an app, env and addon name strings, the conduit command
    calls start_conduit with app, env, addon type and addon name."""

    mock_conduit_instance = mock_conduit_object.return_value
    mock_conduit_instance.start.side_effect = SecretNotFoundError()
    addon_name = "adasf"
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

    print(result.output)
    err = ""

    mock_click.assert_called_with(
        f"""No secret called "{err}" for "test-application" in "development" environment.""",
        fg="red",
    )

    assert result.exit_code == 1

    validate_version.assert_called_once()
    mock_conduit_instance.start.assert_called_with("development", addon_name, "read")


@patch("dbt_platform_helper.commands.conduit.Conduit")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=True),
)
@patch("dbt_platform_helper.commands.conduit.load_application")
@patch("click.secho")
def test_start_conduit_exception_addon_not_found(
    mock_click, mock_application, mock_conduit_object, validate_version
):
    """Test that given an app, env and addon name strings, the conduit command
    calls start_conduit with app, env, addon type and addon name."""

    mock_conduit_instance = mock_conduit_object.return_value
    mock_conduit_instance.start.side_effect = AddonNotFoundError()
    addon_name = "addon"
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

    assert result.exit_code == 1

    mock_click.assert_called_with(
        f"""Addon "{addon_name}" does not exist.""",
        fg="red",
    )

    validate_version.assert_called_once()
    mock_conduit_instance.start.assert_called_with("development", addon_name, "read")


@patch("dbt_platform_helper.commands.conduit.Conduit")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=True),
)
@patch("dbt_platform_helper.commands.conduit.load_application")
@patch("click.secho")
def test_start_conduit_exception_task_timeout(
    mock_click, mock_application, mock_conduit_object, validate_version
):
    """Test that given an app, env and addon name strings, the conduit command
    calls start_conduit with app, env, addon type and addon name."""

    app_name = "test-application"
    env = "development"
    mock_conduit_instance = mock_conduit_object.return_value
    mock_conduit_instance.start.side_effect = CreateTaskTimeoutError()
    addon_name = "addon"
    result = CliRunner().invoke(
        conduit,
        [
            addon_name,
            "--app",
            app_name,
            "--env",
            env,
        ],
    )

    assert result.exit_code == 1

    mock_click.assert_called_with(
        f"""Client ({addon_name}) ECS task has failed to start for "{app_name}" in "{env}" environment.""",
        fg="red",
    )

    validate_version.assert_called_once()
    mock_conduit_instance.start.assert_called_with("development", addon_name, "read")


@patch("dbt_platform_helper.commands.conduit.Conduit")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=True),
)
@patch("dbt_platform_helper.commands.conduit.load_application")
@patch("click.secho")
def test_start_conduit_exception_no_cluster(
    mock_click, mock_application, mock_conduit_object, validate_version
):
    """Test that given an app, env and addon name strings, the conduit command
    calls start_conduit with app, env, addon type and addon name."""

    app_name = "test-application"
    env = "development"
    mock_conduit_instance = mock_conduit_object.return_value
    mock_conduit_instance.start.side_effect = NoClusterError()
    addon_name = "adasf"
    result = CliRunner().invoke(
        conduit,
        [
            addon_name,
            "--app",
            app_name,
            "--env",
            env,
        ],
    )

    assert result.exit_code == 1

    mock_click.assert_called_with(
        f"""No ECS cluster found for "{app_name}" in "{env}" environment.""", fg="red"
    )

    validate_version.assert_called_once()
    mock_conduit_instance.start.assert_called_with("development", addon_name, "read")


@patch("dbt_platform_helper.commands.conduit.Conduit")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=True),
)
@patch("dbt_platform_helper.commands.conduit.load_application")
@patch("click.secho")
def test_start_conduit_exception_parameter_not_found(
    mock_click, mock_application, mock_conduit_object, validate_version
):
    """Test that given an app, env and addon name strings, the conduit command
    calls start_conduit with app, env, addon type and addon name."""

    app_name = "test-application"
    env = "development"
    mock_conduit_instance = mock_conduit_object.return_value
    mock_conduit_instance.start.side_effect = ParameterNotFoundError()
    addon_name = "adasf"
    result = CliRunner().invoke(
        conduit,
        [
            addon_name,
            "--app",
            app_name,
            "--env",
            env,
        ],
    )

    assert result.exit_code == 1

    mock_click.assert_called_with(
        f"""No parameter called "/copilot/applications/{app_name}/environments/{env}/addons". Try deploying the "{app_name}" "{env}" environment.""",
        fg="red",
    )

    validate_version.assert_called_once()
    mock_conduit_instance.start.assert_called_with("development", addon_name, "read")


@patch("dbt_platform_helper.commands.conduit.Conduit")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=True),
)
@patch("dbt_platform_helper.commands.conduit.load_application")
@patch("click.secho")
def test_start_conduit_exception_invalid_addon_type(
    mock_click, mock_application, mock_conduit_object, validate_version
):
    """Test that given an app, env and addon name strings, the conduit command
    calls start_conduit with app, env, addon type and addon name."""

    addon_type = "fake-postgres"
    mock_conduit_instance = mock_conduit_object.return_value
    mock_conduit_instance.start.side_effect = InvalidAddonTypeError(addon_type=addon_type)
    addon_name = "adasf"
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

    assert result.exit_code == 1

    mock_click.assert_called_with(
        f"""Addon type "{addon_type}" is not supported, we support: opensearch, postgres, redis..""",
        fg="red",
    )
    validate_version.assert_called_once()
    mock_conduit_instance.start.assert_called_with("development", addon_name, "read")
