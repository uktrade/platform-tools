from unittest.mock import Mock
from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.job import ls
from dbt_platform_helper.commands.job import run
from dbt_platform_helper.platform_exception import PlatformException


@patch("dbt_platform_helper.commands.job.JobManager")
@patch("dbt_platform_helper.commands.job.StepFunctions")
@patch("dbt_platform_helper.commands.job.load_application")
def test_job_run(mock_application, mock_step_functions, mock_job_manager_object):
    """Test that given an app, env and job name strings, the job run command
    calls run with app, env and job name."""

    mock_job_manager_instance = mock_job_manager_object.return_value

    result = CliRunner().invoke(
        run,
        ["--app", "test-application", "--env", "development", "--name", "test-job"],
    )

    assert result.exit_code == 0

    mock_application.assert_called_once_with(app="test-application", env="development")
    mock_step_functions.assert_called_once()
    mock_job_manager_instance.start_execution.assert_called_once_with(
        "test-application", "development", "test-job", False
    )


@patch("dbt_platform_helper.commands.job.JobManager")
@patch("dbt_platform_helper.commands.job.StepFunctions")
@patch("dbt_platform_helper.commands.job.load_application")
@patch("dbt_platform_helper.commands.job.ClickIOProvider")
def test_job_run_fail(mock_io, mock_application, mock_step_functions, mock_job_manager_object):
    """Test that job run command handles exceptions gracefully."""

    mock_job_manager_instance = mock_job_manager_object.return_value
    mock_job_manager_instance.start_execution.side_effect = PlatformException("Job not found")
    mock_io.return_value.abort_with_error.side_effect = SystemExit(1)

    result = CliRunner().invoke(
        run,
        ["--app", "test-application", "--env", "development", "--name", "test-job"],
    )

    assert result.exit_code == 1
    mock_io.return_value.abort_with_error.assert_called_once_with("Job not found")


@patch("dbt_platform_helper.commands.job.JobManager")
@patch("dbt_platform_helper.commands.job.StepFunctions")
@patch("dbt_platform_helper.commands.job.load_application")
def test_job_run_missing_required_arguments(
    mock_application, mock_step_functions, mock_job_manager_object
):
    """Test that job run command requires all arguments."""

    result = CliRunner().invoke(run, [])

    assert result.exit_code != 0
    assert "Error" in result.output and "Missing option" in result.output


@patch("dbt_platform_helper.commands.job.JobManager")
@patch("dbt_platform_helper.commands.job.StepFunctions")
@patch("dbt_platform_helper.commands.job.load_application")
def test_job_run_with_optional_follow(
    mock_application, mock_step_functions, mock_job_manager_object
):
    """Test that given an app, env and job name strings, the job run command
    calls run with app, env and job name."""

    mock_job_manager_instance = mock_job_manager_object.return_value

    result = CliRunner().invoke(
        run,
        ["--app", "test-application", "--env", "development", "--name", "test-job", "--follow"],
    )

    assert result.exit_code == 0

    mock_application.assert_called_once_with(app="test-application", env="development")
    mock_step_functions.assert_called_once()
    mock_job_manager_instance.start_execution.assert_called_once_with(
        "test-application", "development", "test-job", True
    )


@patch("dbt_platform_helper.commands.job.JobManager")
@patch("dbt_platform_helper.commands.job.StepFunctions")
@patch("dbt_platform_helper.commands.job.load_application")
@patch("dbt_platform_helper.commands.job.ServiceRepository")
def test_job_list(
    mock_service_repository, mock_application, mock_step_functions, mock_job_manager_object
):
    """Test that given an app, env and job name strings, the job run command
    calls run with app, env and job name."""

    mock_job_manager_instance = mock_job_manager_object.return_value

    result = CliRunner().invoke(
        ls,
        ["--app", "test-application", "--env", "development"],
    )

    assert result.exit_code == 0

    mock_application.assert_called_once_with(app="test-application", env="development")
    mock_job_manager_instance.list_jobs.assert_called_once_with("test-application", "development")


@patch("dbt_platform_helper.commands.job.load_application")
@patch("dbt_platform_helper.commands.job.ClickIOProvider")
def test_job_list_raises_given_wrong_environment(mock_io, mock_application):
    """Test that given an app, env and job name strings, the job run command
    calls run with app, env and job name."""
    mock_application_instance = Mock()
    mock_application_instance.environments = {"development": {}}

    mock_application.return_value = mock_application_instance

    mock_io_instance = Mock()
    mock_io.return_value = mock_io_instance

    result = CliRunner().invoke(
        ls,
        ["--app", "test-application", "--env", "wrong-environment"],
    )

    mock_io_instance.abort_with_error.assert_called_with(
        'The environment "wrong-environment" either does not exist or has not been deployed for the application test-application.'
    )
