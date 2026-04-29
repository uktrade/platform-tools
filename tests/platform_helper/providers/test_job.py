from unittest.mock import Mock

import pytest

from dbt_platform_helper.providers.step_functions import (
    MultipleStateMachinesFoundException,
)
from dbt_platform_helper.providers.step_functions import StateMachineNotFoundException
from dbt_platform_helper.providers.step_functions import StepFunctions


def make_paginated_client(state_machines):
    client = Mock()
    arns = [arn for arn, _ in state_machines]
    paginator = Mock()
    paginator.paginate.return_value = [
        {"stateMachines": [{"stateMachineArn": arn} for arn in arns]}
    ]

    client.get_paginator.return_value = paginator

    tags_by_arn = {arn: tags for arn, tags in state_machines}
    client.list_tags_for_resource.side_effect = lambda resourceArn: {
        "tags": [{"key": k, "value": v} for k, v in tags_by_arn[resourceArn].items()]
    }
    return client


def test_find_state_machine_arn_returns_arn_when_tags_match():
    client = make_paginated_client(
        [
            (
                "arn:aws:states:::stateMachine:test-hello-world",
                {
                    "copilot-application": "test-app",
                    "copilot-environment": "dev",
                    "copilot-service": "hello-world",
                },
            ),
        ]
    )

    provider = StepFunctions(client, application_name="test-app", env="dev")
    result = provider._find_state_machine_arn("hello-world")

    assert result == "arn:aws:states:::stateMachine:test-hello-world"


def test_find_state_machine_arn_raises_when_not_found():
    client = make_paginated_client(
        [
            (
                "arn:other",
                {
                    "copilot-application": "different-app",
                    "copilot-environment": "staging",
                    "copilot-service": "different-job",
                },
            ),
        ]
    )

    provider = StepFunctions(client, application_name="test-app", env="dev")
    with pytest.raises(StateMachineNotFoundException):
        provider._find_state_machine_arn("hello-world")


def test_find_state_machine_arn_raises_when_multiple_found():

    tags = {
        "copilot-application": "test-app",
        "copilot-environment": "dev",
        "copilot-service": "hello-world",
    }

    client = make_paginated_client(
        [
            ("arn:duplicate-one", tags),
            ("arn:duplicate-two", tags),
        ]
    )

    provider = StepFunctions(client, application_name="test-app", env="dev")
    with pytest.raises(MultipleStateMachinesFoundException):
        provider._find_state_machine_arn("hello-world")


def test_get_status():
    client = Mock()
    client.describe_execution.return_value = {
        "executionArn": "arn:exec:123",
        "status": "RUNNING",
    }

    provider = StepFunctions(client, application_name="test-app", env="dev")

    status = provider.get_status("arn:exec:123")

    assert status == "RUNNING"
