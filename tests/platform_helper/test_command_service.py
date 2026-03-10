from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.service import service


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
        "test-application", "development", "test-service"
    )
