from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from dbt_platform_helper.exceptions import ECSAgentNotRunning
from dbt_platform_helper.exceptions import NoClusterError
from dbt_platform_helper.providers.ecs import ECS
from tests.platform_helper.conftest import mock_parameter_name
from tests.platform_helper.conftest import mock_task_name


@mock_aws
def test_get_cluster_arn(mocked_cluster, mock_application):
    ecs_client = mock_application.environments["development"].session.client("ecs")
    ssm_client = mock_application.environments["development"].session.client("ssm")
    application_name = mock_application.name
    env = "development"
    ecs_manager = ECS(ecs_client, ssm_client, application_name, env)

    cluster_arn = ecs_manager.get_cluster_arn()

    assert cluster_arn == mocked_cluster["cluster"]["clusterArn"]


@mock_aws
def test_get_cluster_arn_with_no_cluster_raises_error(mock_application):
    ecs_client = mock_application.environments["development"].session.client("ecs")
    ssm_client = mock_application.environments["development"].session.client("ssm")
    application_name = mock_application.name
    env = "does-not-exist"

    ecs_manager = ECS(ecs_client, ssm_client, application_name, env)

    with pytest.raises(NoClusterError):
        ecs_manager.get_cluster_arn()


@mock_aws
def test_get_ecs_task_arns_with_running_task(
    mock_cluster_client_task, mocked_cluster, mock_application
):
    addon_type = "redis"
    mock_cluster_client_task(addon_type)
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    ecs_client = mock_application.environments["development"].session.client("ecs")
    ecs_manager = ECS(
        ecs_client,
        mock_application.environments["development"].session.client("ssm"),
        mock_application.name,
        "development",
    )
    assert ecs_manager.get_ecs_task_arns(mocked_cluster_arn, mock_task_name(addon_type))


@mock_aws
def test_get_ecs_task_arns_with_no_running_task(mocked_cluster, mock_application):
    addon_type = "opensearch"
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    ecs_client = mock_application.environments["development"].session.client("ecs")
    ecs_manager = ECS(
        ecs_client,
        mock_application.environments["development"].session.client("ssm"),
        mock_application.name,
        "development",
    )
    assert len(ecs_manager.get_ecs_task_arns(mocked_cluster_arn, mock_task_name(addon_type))) == 0


@mock_aws
def test_get_ecs_task_arns_does_not_return_arns_from_other_tasks(mock_application, mocked_cluster):
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
    ecs_manager = ECS(
        ecs_client,
        mock_application.environments["development"].session.client("ssm"),
        mock_application.name,
        "development",
    )
    assert len(ecs_manager.get_ecs_task_arns(cluster_arn, task_name)) == 0


@mock_aws
def test_ecs_exec_is_available(mock_cluster_client_task, mocked_cluster, mock_application):
    mocked_ecs_client = mock_cluster_client_task("postgres")
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    ecs_manager = ECS(
        mocked_ecs_client,
        mock_application.environments["development"].session.client("ssm"),
        mock_application.name,
        "development",
    )
    ecs_manager.ecs_exec_is_available(
        mocked_cluster_arn, ["arn:aws:ecs:eu-west-2:12345678:task/does-not-matter/1234qwer"]
    )


@patch("time.sleep", return_value=None)
@mock_aws
def test_ecs_exec_is_available_with_exec_not_running_raises_exception(
    sleep, mock_cluster_client_task, mocked_cluster, mock_application
):
    mocked_ecs_client = mock_cluster_client_task("postgres", "PENDING")
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    ecs_manager = ECS(
        mocked_ecs_client,
        mock_application.environments["development"].session.client("ssm"),
        mock_application.name,
        "development",
    )
    with pytest.raises(ECSAgentNotRunning):
        ecs_manager.ecs_exec_is_available(
            mocked_cluster_arn, ["arn:aws:ecs:eu-west-2:12345678:task/does-not-matter/1234qwer"]
        )


@mock_aws
def test_get_or_create_task_name(mock_application):
    addon_name = "app-postgres"
    parameter_name = mock_parameter_name(mock_application, "postgres", addon_name)
    mock_application.environments["development"].session.client("ssm")
    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name=parameter_name,
        Type="String",
        Value=mock_task_name(addon_name),
    )
    ecs_manager = ECS(
        mock_application.environments["development"].session.client("ecs"),
        mock_ssm,
        mock_application.name,
        "development",
    )
    task_name = ecs_manager.get_or_create_task_name(addon_name, parameter_name)
    assert task_name == mock_task_name(addon_name)


@mock_aws
def test_get_or_create_task_name_appends_random_id(mock_application):
    addon_name = "app-postgres"
    ssm_client = mock_application.environments["development"].session.client("ssm")
    parameter_name = mock_parameter_name(mock_application, "postgres", addon_name)
    ecs_manager = ECS(ssm_client, ssm_client, mock_application.name, "development")

    task_name = ecs_manager.get_or_create_task_name(addon_name, parameter_name)
    random_id = task_name.rsplit("-", 1)[1]

    assert task_name.rsplit("-", 1)[0] == mock_task_name("app-postgres").rsplit("-", 1)[0]
    assert random_id.isalnum() and random_id.islower() and len(random_id) == 12
