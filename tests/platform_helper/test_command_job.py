from unittest.mock import patch

from click.testing import CliRunner

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
    mock_job_manager_instance.run.assert_called_once_with(
        "test-application", "development", "test-job"
    )


@patch("dbt_platform_helper.commands.job.JobManager")
@patch("dbt_platform_helper.commands.job.StepFunctions")
@patch("dbt_platform_helper.commands.job.load_application")
@patch("dbt_platform_helper.commands.job.ClickIOProvider")
def test_job_run_fail(mock_io, mock_application, mock_step_functions, mock_job_manager_object):
    """Test that job run command handles exceptions gracefully."""

    mock_job_manager_instance = mock_job_manager_object.return_value
    mock_job_manager_instance.run.side_effect = PlatformException("Job not found")
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
    assert "Error" in result.output or "Missing option" in result.output


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
    mock_job_manager_instance.run.assert_called_once_with(
        "test-application", "development", "test-job"
    )
