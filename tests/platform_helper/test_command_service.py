from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.service import service
from dbt_platform_helper.platform_exception import PlatformException


@patch("dbt_platform_helper.commands.service.ServiceManager")
@patch("dbt_platform_helper.commands.service.load_application")
def test_service_exec(mock_application, mock_service_manager_object):
    """Test that given an app, env and service name strings, the service exec
    command calls exec with app, env and service name."""

    mock_service_manager_instance = mock_service_manager_object.return_value

    result = CliRunner().invoke(
        service,
        ["exec", "--app", "test-application", "--env", "development", "--name", "test-service"],
    )

    assert result.exit_code == 0

    mock_application.assert_called_once()
    mock_service_manager_instance.service_exec.assert_called_with(
        "test-application", "development", "test-service", None, None, None
    )


@patch("dbt_platform_helper.commands.service.ServiceManager")
@patch("dbt_platform_helper.commands.service.load_application")
def test_service_exec_with_optional_arguments(mock_application, mock_service_manager_object):
    """Test that given an app, env and service name strings, the service exec
    command calls exec with app, env and service name."""

    mock_service_manager_instance = mock_service_manager_object.return_value

    result = CliRunner().invoke(
        service,
        [
            "exec",
            "--app",
            "test-application",
            "--env",
            "development",
            "--name",
            "test-service",
            "--container",
            "my-container",
            "--command",
            "pwd",
            "--task-id",
            "my-task",
        ],
    )

    assert result.exit_code == 0

    mock_application.assert_called_once()
    mock_service_manager_instance.service_exec.assert_called_with(
        "test-application", "development", "test-service", "pwd", "my-container", "my-task"
    )


@patch("dbt_platform_helper.commands.service.ServiceManager")
@patch("dbt_platform_helper.commands.service.load_application")
@patch("dbt_platform_helper.commands.service.ClickIOProvider")
def test_service_exec_fail(mock_io, mock_application, mock_service_manager_object):
    """Test that given an app, env and service name strings, the service exec
    command calls exec with app, env and service name."""

    mock_service_manager_instance = mock_service_manager_object.return_value
    mock_service_manager_instance.service_exec.side_effect = PlatformException("Some weird error")
    mock_io.return_value.abort_with_error.side_effect = SystemExit(1)

    result = CliRunner().invoke(
        service,
        ["exec", "--app", "test-application", "--env", "development", "--name", "test-service"],
    )

    assert result.exit_code == 1

    mock_application.assert_called_once()
    mock_service_manager_instance.service_exec.assert_called_with(
        "test-application", "development", "test-service", None, None, None
    )
    mock_io.return_value.abort_with_error.assert_called_once_with("Some weird error")
