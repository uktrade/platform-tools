from unittest.mock import Mock
from unittest.mock import patch

import pytest

from dbt_platform_helper.domain.job import JobManager
from dbt_platform_helper.domain.job import ScheduledJobExecutionFailedException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.service import Service
from dbt_platform_helper.providers.service import ServiceRepository
from dbt_platform_helper.providers.step_functions import StepFunctions


@patch("dbt_platform_helper.domain.job.time.sleep")
def test_follow_execution_returns_when_succeeded(mock_sleep):
    mock_sfn = Mock(spec=StepFunctions)
    mock_sfn.get_status.return_value = "SUCCEEDED"
    manager = JobManager(job_runner=mock_sfn)

    manager.follow_execution("arn:exec:123")

    mock_sfn.get_status.assert_called_once_with("arn:exec:123")


@patch("dbt_platform_helper.domain.job.time.sleep")
def test_follow_execution_raises_when_fails(mock_sleep):
    mock_sfn = Mock(spec=StepFunctions)
    mock_sfn.get_status.return_value = "FAILED"
    manager = JobManager(job_runner=mock_sfn)

    with pytest.raises(ScheduledJobExecutionFailedException):
        manager.follow_execution("arn:exec:123")


@patch("dbt_platform_helper.domain.job.time.sleep")
def test_follow_execution_polls_until_succeeded(mock_sleep):
    mock_sfn = Mock(spec=StepFunctions)
    mock_sfn.get_status.side_effect = ["RUNNING", "RUNNING", "SUCCEEDED"]
    manager = JobManager(job_runner=mock_sfn)

    manager.follow_execution("arn:exec:123")

    assert mock_sfn.get_status.call_count == 3


@patch("dbt_platform_helper.domain.job.time.sleep")
def test_follow_execution_polls_until_fails(mock_sleep):
    mock_sfn = Mock(spec=StepFunctions)
    mock_sfn.get_status.side_effect = ["RUNNING", "RUNNING", "FAILED"]
    manager = JobManager(job_runner=mock_sfn)

    with pytest.raises(ScheduledJobExecutionFailedException):
        manager.follow_execution("arn:exec:123")


def test_list_jobs():
    mock_io = Mock(spec=ClickIOProvider)

    mock_repository = Mock(spec=ServiceRepository)
    mock_repository.list_jobs.return_value = [Service("test-job", "test")]

    manager = JobManager(job_runner=None, service_repository=mock_repository, io=mock_io)

    manager.list_jobs("test-app", "test-env")

    mock_io.info.assert_called_with(
        f"Scheduled Jobs currently deployed for test-app in the test-env environment:\ntest-job"
    )
