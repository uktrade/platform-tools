from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from dbt_platform_helper.exceptions import ECSAgentNotRunning
from dbt_platform_helper.exceptions import NoClusterError
from dbt_platform_helper.providers.ecs import ecs_exec_is_available
from dbt_platform_helper.providers.ecs import get_cluster_arn
from dbt_platform_helper.providers.ecs import get_ecs_task_arns
from dbt_platform_helper.providers.ecs import get_or_create_task_name
from tests.platform_helper.conftest import mock_parameter_name
from tests.platform_helper.conftest import mock_task_name


@mock_aws
def test_get_cluster_arn(mocked_cluster, mock_application):
    """Test that, given app and environment strings, get_cluster_arn returns the
    arn of a cluster tagged with these strings."""

    assert (
        get_cluster_arn(
            mock_application.environments["development"].session.client("ecs"),
            mock_application.name,
            "development",
        )
        == mocked_cluster["cluster"]["clusterArn"]
    )


@mock_aws
def test_get_cluster_arn_with_no_cluster_raises_error(mock_application):
    with pytest.raises(NoClusterError):
        get_cluster_arn(
            mock_application.environments["staging"].session.client("ecs"),
            mock_application.name,
            "staging",
        )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_get_ecs_task_arns_with_running_task(
    mock_cluster_client_task, mocked_cluster, addon_type, mock_application
):

    mock_cluster_client_task(addon_type)
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    ecs_client = mock_application.environments["development"].session.client("ecs")

    assert get_ecs_task_arns(ecs_client, mocked_cluster_arn, mock_task_name(addon_type))


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_get_ecs_task_arns_with_no_running_task(mocked_cluster, addon_type, mock_application):

    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    ecs_client = mock_application.environments["development"].session.client("ecs")

    assert len(get_ecs_task_arns(ecs_client, mocked_cluster_arn, mock_task_name(addon_type))) is 0


@mock_aws
@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_get_ecs_task_arns_does_not_return_arns_from_other_tasks(
    addon_type, mock_application, mocked_cluster
):
    ecs_client = mock_application.environments["development"].session.client("ecs")
    cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    task_name = "no-running-task"
    ec2 = boto3.resource("ec2")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    mocked_task_definition_arn = ecs_client.register_task_definition(
        family=f"other-task",
        requiresCompatibilities=["FARGATE"],
        networkMode="awsvpc",
        containerDefinitions=[
            {
                "name": "test_container",
                "image": "test_image",
                "cpu": 256,
                "memory": 512,
                "essential": True,
            }
        ],
    )["taskDefinition"]["taskDefinitionArn"]
    ecs_client.run_task(
        taskDefinition=mocked_task_definition_arn,
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": [subnet.id],
                "securityGroups": ["something-sg"],
            }
        },
    )

    assert len(get_ecs_task_arns(ecs_client, cluster_arn, task_name)) is 0


def test_check_if_ecs_exec_is_availble_success(
    mock_cluster_client_task, mocked_cluster, mock_application
):

    # use mock ecs_client as describe_tasks is overriden
    mocked_ecs_client = mock_cluster_client_task("postgres")
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]

    ecs_exec_is_available(
        mocked_ecs_client,
        mocked_cluster_arn,
        ["arn:aws:ecs:eu-west-2:12345678:task/does-not-matter/1234qwer"],
    )


@patch("time.sleep", return_value=None)
def test_addon_client_and_exec_is_not_running(
    sleep, mock_cluster_client_task, mocked_cluster, mock_application
):

    # use mock ecs_client as describe_tasks is overriden
    mocked_ecs_client = mock_cluster_client_task("postgres", "PENDING")
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]

    with pytest.raises(ECSAgentNotRunning):
        ecs_exec_is_available(
            mocked_ecs_client,
            mocked_cluster_arn,
            ["arn:aws:ecs:eu-west-2:12345678:task/does-not-matter/1234qwer"],
        )


@mock_aws
def test_get_or_create_task_name(mock_application):
    """Test that get_or_create_task_name retrieves the task name from the
    parameter store when it has been stored."""

    addon_name = "app-postgres"
    parameter_name = mock_parameter_name(mock_application, "postgres", addon_name)
    mock_application.environments["development"].session.client("ssm")
    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name=parameter_name,
        Type="String",
        Value=mock_task_name(addon_name),
    )

    task_name = get_or_create_task_name(
        mock_ssm, mock_application.name, "development", addon_name, parameter_name
    )

    assert task_name == mock_task_name(addon_name)


@mock_aws
def test_get_or_create_task_name_when_name_does_not_exist(mock_application):
    """Test that get_or_create_task_name creates the task name and appends it
    with a 12 digit lowercase alphanumeric string when it does not exist in the
    parameter store."""

    addon_name = "app-postgres"
    ssm_client = mock_application.environments["development"].session.client("ssm")
    parameter_name = mock_parameter_name(mock_application, "postgres", addon_name)
    task_name = get_or_create_task_name(
        ssm_client, mock_application.name, "development", addon_name, parameter_name
    )
    random_id = task_name.rsplit("-", 1)[1]

    assert task_name.rsplit("-", 1)[0] == mock_task_name("app-postgres").rsplit("-", 1)[0]
    assert random_id.isalnum() and random_id.islower() and len(random_id) == 12
