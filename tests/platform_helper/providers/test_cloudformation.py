import json
from unittest.mock import Mock
from unittest.mock import patch

import boto3
import pytest
from botocore.exceptions import WaiterError
from botocore.stub import Stubber
from cfn_tools import load_yaml
from moto import mock_aws

from dbt_platform_helper.providers.cloudformation import CloudFormation
from dbt_platform_helper.providers.cloudformation import CloudFormationException
from tests.platform_helper.conftest import mock_parameter_name
from tests.platform_helper.conftest import mock_task_name

env = "development"


@mock_aws
@pytest.mark.parametrize(
    "addon_type, addon_name, parameter_suffix, env",
    [
        ("postgres", "custom-name-postgres", "_READ_ONLY", "development"),
        ("postgres", "custom-name-rds-postgres", "_READ_ONLY", "development"),
        ("redis", "custom-name-redis", "", "development"),
        ("opensearch", "custom-name-opensearch", "", "development"),
        ("postgres", "custom-prod-name-postgres", "", "production"),
    ],
)
def test_update_conduit_stack_resources(
    mock_stack, addon_type, addon_name, parameter_suffix, env, mock_application
):
    """Test that, given app, env and addon name update_conduit_stack_resources
    updates the conduit CloudFormation stack to add DeletionPolicy:Retain and
    subscription filter to the LogGroup."""

    boto3.client("iam").create_role(
        RoleName="CWLtoSubscriptionFilterRole",
        AssumeRolePolicyDocument="123",
    )

    ssm_response = {
        "prod": "arn:aws:logs:eu-west-2:prod_account_id:destination:test_log_destination",
        "dev": "arn:aws:logs:eu-west-2:dev_account_id:destination:test_log_destination",
    }
    boto3.client("ssm").put_parameter(
        Name="/copilot/tools/central_log_groups",
        Value=json.dumps(ssm_response),
        Type="String",
    )

    mock_stack(addon_name)
    task_name = mock_task_name(addon_name)
    parameter_name = mock_parameter_name(mock_application, addon_type, addon_name)
    cloudformation_client = mock_application.environments[env].session.client("cloudformation")
    iam_client = mock_application.environments[env].session.client("iam")
    ssm_client = mock_application.environments[env].session.client("ssm")

    cloudformation = CloudFormation(cloudformation_client, iam_client, ssm_client)

    cloudformation.update_conduit_stack_resources(
        mock_application.name, env, addon_type, addon_name, task_name, parameter_name, "read"
    )

    template = boto3.client("cloudformation").get_template(StackName=f"task-{task_name}")
    stack = boto3.client("cloudformation").describe_stacks(StackName=f"task-{task_name}")
    template_yml = load_yaml(template["TemplateBody"])

    params = []
    if "Parameters" in template_yml:
        for param in template_yml["Parameters"]:
            params.append({"ParameterKey": param, "UsePreviousValue": True})

    assert stack["Stacks"][0]["Parameters"][0]["ParameterValue"] == "does-not-matter"
    assert template_yml["Resources"]["LogGroup"]["DeletionPolicy"] == "Retain"
    assert template_yml["Resources"]["TaskNameParameter"]["Properties"]["Name"] == parameter_name
    assert (
        template_yml["Resources"]["SubscriptionFilter"]["Properties"]["LogGroupName"]
        == f"/copilot/{task_name}"
    )
    assert ("dev_account_id" if "dev" in env else "prod_account_id") in template_yml["Resources"][
        "SubscriptionFilter"
    ]["Properties"]["DestinationArn"]
    assert (
        template_yml["Resources"]["SubscriptionFilter"]["Properties"]["FilterName"]
        == f"/copilot/conduit/{mock_application.name}/{env}/{addon_type}/{addon_name}/{task_name.rsplit('-', 1)[1]}/read"
    )
    assert len(params) == len(
        template_yml.get("Parameters", [])
    ), "The number of parameters does not match"


@mock_aws
@pytest.mark.parametrize(
    "addon_name",
    ["postgres", "redis", "opensearch", "rds-postgres"],
)
@patch("time.sleep", return_value=None)
def test_add_stack_delete_policy_to_task_role(sleep, mock_stack, addon_name, mock_application):
    """Test that, given app, env and addon name,
    add_stack_delete_policy_to_task_role adds a policy to the IAM role in a
    CloudFormation stack."""

    task_name = mock_task_name(addon_name)
    stack_name = f"task-{task_name}"
    cloudformation_client = mock_application.environments[env].session.client("cloudformation")
    iam_client = mock_application.environments[env].session.client("iam")

    mock_stack(addon_name)
    mock_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": ["cloudformation:DeleteStack"],
                "Effect": "Allow",
                "Resource": f"arn:aws:cloudformation:*:*:stack/{stack_name}/*",
            },
        ],
    }

    cloudformation = CloudFormation(cloudformation_client, iam_client, None)

    cloudformation.add_stack_delete_policy_to_task_role(task_name)

    stack_resources = boto3.client("cloudformation").list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]

    policy_name = None
    policy_document = None
    for resource in stack_resources:
        if resource["LogicalResourceId"] == "DefaultTaskRole":
            policy = boto3.client("iam").get_role_policy(
                RoleName=resource["PhysicalResourceId"], PolicyName="DeleteCloudFormationStack"
            )
            policy_name = policy["PolicyName"]
            policy_document = policy["PolicyDocument"]

    assert policy_name == "DeleteCloudFormationStack"
    assert policy_document == mock_policy


@mock_aws
def test_wait_for_cloudformation_with_no_success_raises_exception():
    cloudformation_client = Mock()
    waiter_mock = Mock()
    cloudformation_client.get_waiter = Mock(return_value=waiter_mock)

    waiter_error = WaiterError(
        "Waiter StackUpdatecomplete failed",
        "Fail!!",
        {"Stacks": [{"StackStatus": "ROLLBACK_IN_PROGRESS"}]},
    )
    waiter_mock.wait.side_effect = waiter_error

    cloudformation = CloudFormation(cloudformation_client, None, None)

    with pytest.raises(
        CloudFormationException,
        match="The CloudFormation stack 'stack-name' is not in a good state: ROLLBACK_IN_PROGRESS",
    ):
        cloudformation.wait_for_cloudformation_to_reach_status(
            "stack_update_complete", "stack-name"
        )


@mock_aws
def test_wait_for_cloudformation_with_update_complete():
    cloudformation_client = Mock()
    waiter_mock = Mock()
    cloudformation_client.get_waiter = Mock(return_value=waiter_mock)
    waiter_mock.wait.return_value = None

    cloudformation = CloudFormation(cloudformation_client, None, None)

    cloudformation.wait_for_cloudformation_to_reach_status("stack_update_complete", "stack-name")

    waiter_mock.wait.assert_called_with(
        StackName="stack-name", WaiterConfig={"Delay": 5, "MaxAttempts": 20}
    )


def test_get_cloudformation_exports_for_environment_gets_expected_exports():

    list_exports_response = {
        "Exports": [
            {"Name": "cnnors-not-so-awesome-env", "Value": "value1"},
            {"Name": "connors-not-so-awesome-env", "Value": "value2"},
            {"Name": "-connors-awesome-env-", "Value": "value3"},
            {"Name": "-connors-awesome-env-", "Value": "value4"},
            {"Name": "connors-not-so-awesome-env", "Value": "value5"},
        ]
    }

    cloudformation_client = boto3.client("cloudformation")
    stubber = Stubber(cloudformation_client)

    stubber.add_response("list_exports", list_exports_response)
    stubber.activate()

    cloudformation = CloudFormation(cloudformation_client, None, None)

    exports_for_environment = cloudformation.get_cloudformation_exports_for_environment(
        "connors-awesome-env"
    )

    assert exports_for_environment == [
        {"Name": "-connors-awesome-env-", "Value": "value3"},
        {"Name": "-connors-awesome-env-", "Value": "value4"},
    ]
