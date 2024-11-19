from unittest.mock import Mock
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from moto import mock_aws

from tests.platform_helper.conftest import add_addon_config_parameter


@mock_aws
@pytest.mark.parametrize(
    "addon_type, addon_name",
    [
        ("postgres", "custom-name-postgres"),
        ("redis", "custom-name-redis"),
        ("opensearch", "custom-name-opensearch"),
    ],
)
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_platform_helper.commands.conduit.start_conduit")
def test_conduit_command(start_conduit, addon_type, addon_name, validate_version, mock_application):
    """Test that given an app, env and addon name strings, the conduit command
    calls start_conduit with app, env, addon type and addon name."""
    from dbt_platform_helper.commands.conduit import conduit

    add_addon_config_parameter()

    CliRunner().invoke(
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
    start_conduit.assert_called_once_with(
        mock_application, "development", addon_type, addon_name, "read"
    )


@mock_aws
@patch("click.secho")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_platform_helper.commands.conduit.start_conduit")
@patch(
    "dbt_platform_helper.commands.conduit.get_addon_type", new=Mock(return_value="mock_addon_type")
)
def test_conduit_command_when_no_cluster_exists(start_conduit, secho, validate_version):
    """Test that given an app, env and addon name strings, when there is no ECS
    Cluster available, the conduit command handles the NoClusterConduitError
    exception."""
    from dbt_platform_helper.commands.conduit import NoClusterConduitError
    from dbt_platform_helper.commands.conduit import conduit

    start_conduit.side_effect = NoClusterConduitError

    result = CliRunner().invoke(
        conduit,
        [
            "mock_addon",
            "--app",
            "test-application",
            "--env",
            "development",
        ],
    )

    assert result.exit_code == 1
    validate_version.assert_called_once()
    secho.assert_called_once_with(
        """No ECS cluster found for "test-application" in "development" environment.""", fg="red"
    )


@mock_aws
@patch("click.secho")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_platform_helper.commands.conduit.start_conduit")
@patch(
    "dbt_platform_helper.commands.conduit.get_addon_type", new=Mock(return_value="mock_addon_type")
)
def test_conduit_command_when_no_connection_secret_exists(start_conduit, secho, validate_version):
    """Test that given an app, env and addon name strings, when there is no
    connection secret available, the conduit command handles the
    NoConnectionSecretError exception."""
    from dbt_platform_helper.commands.conduit import SecretNotFoundConduitError
    from dbt_platform_helper.commands.conduit import conduit

    mock_addon_name = "mock_addon"
    start_conduit.side_effect = SecretNotFoundConduitError(mock_addon_name)

    result = CliRunner().invoke(
        conduit,
        [
            mock_addon_name,
            "--app",
            "test-application",
            "--env",
            "development",
        ],
    )

    assert result.exit_code == 1
    validate_version.assert_called_once()
    secho.assert_called_once_with(
        f"""No secret called "{mock_addon_name}" for "test-application" in "development" environment.""",
        fg="red",
    )


@mock_aws
@patch("click.secho")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_platform_helper.commands.conduit.start_conduit")
@patch(
    "dbt_platform_helper.commands.conduit.get_addon_type", new=Mock(return_value="mock_addon_type")
)
def test_conduit_command_when_client_task_fails_to_start(start_conduit, secho, validate_version):
    """Test that given an app, env and addon name strings, when the ECS client
    task fails to start, the conduit command handles the
    TaskConnectionTimeoutError exception."""
    from dbt_platform_helper.commands.conduit import CreateTaskTimeoutConduitError
    from dbt_platform_helper.commands.conduit import conduit

    mock_addon_name = "mock_addon"
    start_conduit.side_effect = CreateTaskTimeoutConduitError

    result = CliRunner().invoke(
        conduit,
        [
            mock_addon_name,
            "--app",
            "test-application",
            "--env",
            "development",
        ],
    )

    assert result.exit_code == 1
    validate_version.assert_called_once()
    secho.assert_called_once_with(
        f"""Client ({mock_addon_name}) ECS task has failed to start for "test-application" in "development" environment.""",
        fg="red",
    )


@mock_aws
@patch("click.secho")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_platform_helper.commands.conduit.start_conduit")
def test_conduit_command_when_addon_type_is_invalid(start_conduit, secho, validate_version):
    """Test that given an app, env and addon name strings, if the addon type is
    invalid the conduit command handles the exception."""
    from dbt_platform_helper.commands.conduit import conduit

    add_addon_config_parameter({"custom-name-postgres": {"type": "nope"}})

    result = CliRunner().invoke(
        conduit,
        [
            "custom-name-postgres",
            "--app",
            "test-application",
            "--env",
            "development",
        ],
    )

    assert result.exit_code == 1
    validate_version.assert_called_once()
    start_conduit.assert_not_called()
    secho.assert_called_once_with(
        """Addon type "nope" is not supported, we support: opensearch, postgres, redis.""",
        fg="red",
    )


@mock_aws
@patch("click.secho")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_platform_helper.commands.conduit.start_conduit")
def test_conduit_command_when_addon_does_not_exist(start_conduit, secho, validate_version):
    """Test that given an app, env and invalid addon name strings, the conduit
    command handles the exception."""
    from dbt_platform_helper.commands.conduit import conduit

    add_addon_config_parameter({"non-existent-addon": {"type": "redis"}})

    result = CliRunner().invoke(
        conduit,
        [
            "custom-name-postgres",
            "--app",
            "test-application",
            "--env",
            "development",
        ],
    )

    assert result.exit_code == 1
    validate_version.assert_called_once()
    start_conduit.assert_not_called()
    secho.assert_called_once_with(
        """Addon "custom-name-postgres" does not exist.""",
        fg="red",
    )


@mock_aws
@patch("click.secho")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
def test_conduit_command_when_no_addon_config_parameter_exists(secho, validate_version):
    """Test that given an app, env and addon name strings, when there is no
    addon config parameter available, the conduit command handles the
    ParameterNotFoundConduitError exception."""
    from dbt_platform_helper.commands.conduit import conduit

    result = CliRunner().invoke(
        conduit,
        [
            "mock_addon",
            "--app",
            "test-application",
            "--env",
            "development",
        ],
    )

    assert result.exit_code == 1
    validate_version.assert_called_once()
    secho.assert_called_once_with(
        f"""No parameter called "/copilot/applications/test-application/environments/development/addons". Try deploying the "test-application" "development" environment.""",
        fg="red",
    )


@mock_aws
@pytest.mark.parametrize("access", ["read", "write", "admin"])
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch("dbt_platform_helper.commands.conduit.start_conduit")
@patch("dbt_platform_helper.commands.conduit.get_addon_type", new=Mock(return_value="postgres"))
def test_conduit_command_flags(
    start_conduit,
    access,
    validate_version,
    mock_application,
):
    """Test that given an app, env, addon name strings and optional permission
    flags, the conduit command calls start_conduit with app, env, addon type,
    addon name and the correct boolean values."""
    from dbt_platform_helper.commands.conduit import conduit

    mock_addon_name = "mock_addon"
    CliRunner().invoke(
        conduit,
        [
            mock_addon_name,
            "--app",
            "test-application",
            "--env",
            "development",
            "--access",
            f"{access}",
        ],
    )

    validate_version.assert_called_once()
    start_conduit.assert_called_once_with(
        mock_application, "development", "postgres", mock_addon_name, access
    )
