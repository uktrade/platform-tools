from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from dbt_platform_helper.providers.step_functions import StartExecutionFailedException
from dbt_platform_helper.providers.step_functions import StateMachineNotFoundException
from dbt_platform_helper.providers.step_functions import StepFunctions


def test_run_constructs_correct_arn():

    sfn_client = Mock()
    sfn_client.meta.region_name = "eu-west-2"
    sfn_client.start_execution.return_value = {"executionArn": "arn:exec:123"}
    job_runner = StepFunctions(
        sfn_client, application_name="demodjango", env="dev", account_id="123456789012"
    )

    job_runner.run("test")

    sfn_client.start_execution.assert_called_once_with(
        stateMachineArn="arn:aws:states:eu-west-2:123456789012:stateMachine:demodjango-dev-test-sfn"
    )


def test_run_returns_correct_arn():

    sfn_client = Mock()
    sfn_client.meta.region_name = "eu-west-2"
    sfn_client.start_execution.return_value = {
        "executionArn": "arn:aws:states:eu-west-2:123456789012:stateMachine:demodjango-dev-test:abc"
    }
    job_runner = StepFunctions(
        sfn_client, application_name="demodjango", env="dev", account_id="123456789012"
    )

    result = job_runner.run("test")

    assert result == "arn:aws:states:eu-west-2:123456789012:stateMachine:demodjango-dev-test:abc"


def test_run_raises_when_state_machine_not_found():

    sfn_client = Mock()
    sfn_client.meta.region_name = "eu-west-2"
    sfn_client.start_execution.side_effect = ClientError(
        {"Error": {"Code": "StateMachineDoesNotExist", "Message": "..."}},
        "StartExecution",
    )
    job_runner = StepFunctions(
        sfn_client, application_name="demodjango", env="dev", account_id="123456789012"
    )

    with pytest.raises(StateMachineNotFoundException):
        job_runner.run("test")


def test_run_raises_when_client_error():
    sfn_client = Mock()
    sfn_client.meta.region_name = "eu-west-2"
    sfn_client.start_execution.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Not allowed"}},
        "StartExecution",
    )

    job_runner = StepFunctions(
        sfn_client, application_name="demodjango", env="dev", account_id="123456789012"
    )

    with pytest.raises(StartExecutionFailedException):
        job_runner.run("test")


def test_get_status():
    client = Mock()
    client.describe_execution.return_value = {
        "executionArn": "arn:exec:123",
        "status": "RUNNING",
    }

    provider = StepFunctions(
        client, application_name="test-app", env="dev", account_id="123456789012"
    )

    status = provider.get_status("arn:exec:123")

    assert status == "RUNNING"
