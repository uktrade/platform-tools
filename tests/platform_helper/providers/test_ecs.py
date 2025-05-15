from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.providers.ecs import NoClusterException
from dbt_platform_helper.providers.vpc import Vpc
from tests.platform_helper.conftest import mock_parameter_name
from tests.platform_helper.conftest import mock_task_name


@mock_aws
def test_get_cluster_arn(mocked_cluster, mock_application):
    ecs_client = mock_application.environments["development"].session.client("ecs")
    ssm_client = mock_application.environments["development"].session.client("ssm")
    application_name = mock_application.name
    env = "development"
    ecs_manager = ECS(ecs_client, ssm_client, application_name, env)

    cluster_arn = ecs_manager.get_cluster_arn_by_name("default")

    assert cluster_arn == mocked_cluster["cluster"]["clusterArn"]


@mock_aws
def test_get_cluster_arn_copilot(mocked_cluster, mock_application):
    ecs_client = mock_application.environments["development"].session.client("ecs")
    ssm_client = mock_application.environments["development"].session.client("ssm")
    application_name = mock_application.name
    env = "development"
    ecs_manager = ECS(ecs_client, ssm_client, application_name, env)

    cluster_arn = ecs_manager.get_cluster_arn_by_copilot_tag()

    assert cluster_arn == mocked_cluster["cluster"]["clusterArn"]


def test_get_cluster_arn_copilot_with_no_cluster_raises_error():
    ecs_client = MagicMock()
    ssm_client = MagicMock()

    ecs_client.list_clusters.return_value = {"clusterArns": []}

    ecs_manager = ECS(ecs_client, ssm_client, application_name="my-app", env="development")

    with pytest.raises(NoClusterException):
        ecs_manager.get_cluster_arn_by_copilot_tag()

    ecs_client.list_clusters.assert_called_once()


def test_get_cluster_arn_with_no_cluster_raises_error():
    ecs_client = MagicMock()
    ssm_client = MagicMock()

    ecs_client.describe_clusters.return_value = {"clusters": []}

    ecs_manager = ECS(ecs_client, ssm_client, application_name="my-app", env="development")

    with pytest.raises(NoClusterException):
        ecs_manager.get_cluster_arn_by_name("does-not_exist")

    ecs_client.describe_clusters.assert_called_once_with(clusters=["does-not_exist"])


def test_get_cluster_arn_by_name_multiple_clusters_returns_error():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.describe_clusters.return_value = {
        "clusters": [
            {"clusterArn": "arn:1"},
            {"clusterArn": "arn:2"},
        ]
    }

    ecs = ECS(ecs_client, ssm_client, "my-app", "development")

    with pytest.raises(NoClusterException):
        ecs.get_cluster_arn_by_name("some-cluster")

    ecs_client.describe_clusters.assert_called_once_with(clusters=["some-cluster"])


def test_get_cluster_arn_by_name_missing_arn_raises():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.describe_clusters.return_value = {"clusters": [{}]}  # Without 'clusterArn' field

    ecs = ECS(ecs_client, ssm_client, "my-app", "development")

    with pytest.raises(NoClusterException):
        ecs.get_cluster_arn_by_name("some-cluster")


def test_get_cluster_arn_by_name_passes_correct_cluster():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.describe_clusters.return_value = {"clusters": [{"clusterArn": "arn:cluster"}]}

    ecs = ECS(ecs_client, ssm_client, "my-app", "development")
    arn = ecs.get_cluster_arn_by_name("my-cluster")

    assert arn == "arn:cluster"
    ecs_client.describe_clusters.assert_called_once_with(clusters=["my-cluster"])


@mock_aws
def test_copilot_get_ecs_task_arns_with_running_task(
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
    assert ecs_manager.get_ecs_task_arns(
        mocked_cluster_arn, f"copilot-{mock_task_name(addon_type)}"
    )


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


# @mock_aws
# def test_ecs_exec_is_available_with_exec_not_running_raises_exception(
#     mock_cluster_client_task, mocked_cluster, mock_application
# ):
#     mocked_ecs_client = mock_cluster_client_task("postgres", "PENDING")
#     mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
#     ecs_manager = ECS(
#         mocked_ecs_client,
#         mock_application.environments["development"].session.client("ssm"),
#         mock_application.name,
#         "development",
#     )
#     with pytest.raises(RetryException, match="ECS Agent Not running"):
#         ecs_manager.ecs_exec_is_available(
#             mocked_cluster_arn, ["arn:aws:ecs:eu-west-2:12345678:task/does-not-matter/1234qwer"]
#         )


def test_ecs_exec_is_available_wrapped_by_wait_until():
    ecs = ECS(MagicMock(), MagicMock(), "name", "development")
    assert ecs.ecs_exec_is_available.__wrapped_by__ == "wait_until"


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


# @mock_aws
# def test_start_ecs_task(mocked_cluster, mock_application):
#     ecs_client = mock_application.environments["development"].session.client("ecs")
#     ssm_client = mock_application.environments["development"].session.client("ssm")
#     application_name = mock_application.name
#     env = "development"
#     mocked_ec2_client = boto3.client("ec2")
#     mocked_ec2_images = mocked_ec2_client.describe_images(Owners=["amazon"])["Images"]
#     mocked_ec2_client.run_instances(
#         ImageId=mocked_ec2_images[0]["ImageId"],
#         MinCount=1,
#         MaxCount=1,
#     )
#     mocked_ec2_instances = boto3.client("ec2").describe_instances()
#     mocked_ec2_instance_id = mocked_ec2_instances["Reservations"][0]["Instances"][0]["InstanceId"]
#
#     mocked_ec2 = boto3.resource("ec2")
#     mocked_ec2_instance = mocked_ec2.Instance(mocked_ec2_instance_id)
#     mocked_instance_id_document = json.dumps(
#         ec2_utils.generate_instance_identity_document(mocked_ec2_instance),
#     )
#
#     ecs_client.register_container_instance(
#         cluster="default",
#         instanceIdentityDocument=mocked_instance_id_document,
#     )
#
#     mocked_task_definition_arn = ecs_client.register_task_definition(
#         family="doesnt-matter",
#         containerDefinitions=[
#             {
#                 "name": "test_container",
#                 "image": "test_image",
#                 "cpu": 256,
#                 "memory": 512,
#                 "essential": True,
#                 "environment": [{"name": "TEST_VAR", "value": "test"}],
#             }
#         ],
#     )["taskDefinition"]["taskDefinitionArn"]
#
#     ecs_manager = ECS(ecs_client, ssm_client, application_name, env)
#     actual_response = ecs_manager.start_ecs_task(
#         "default",
#         "test_container",
#         mocked_task_definition_arn,
#         Vpc("test-vpc", ["public-subnet"], ["private-subnet"], ["security-group"]),
#         [{"name": "TEST_VAR", "value": "test"}],
#     )
#
#     assert actual_response.startswith("arn:aws:ecs:")
#
#     task_details = ecs_client.describe_tasks(cluster="default", tasks=[actual_response])
#     assert task_details["tasks"][0]["containers"][0]["name"] == "test_container"
#     assert task_details["tasks"][0]["overrides"]["containerOverrides"][0]["environment"] == [
#         {"name": "TEST_VAR", "value": "test"}
#     ]


def test_start_ecs_task():
    # Prepare
    mock_ecs_client = MagicMock()
    ecs = ECS(mock_ecs_client, MagicMock(), "myapp", "development")
    mock_ecs_client.run_task.return_value = {
        "tasks": [{"taskArn": "arn:aws:ecs:region::task/task-id"}]
    }

    vpc = Vpc("test-vpc", ["public-subnet"], ["private-subnet"], ["security-group"])

    # Test
    task_arn = ecs.start_ecs_task(
        cluster_name="my-cluster",
        container_name="test-container",
        task_def_arn="test-task-def",
        vpc_config=vpc,
        env_vars=[{"name": "TEST_VAR", "value": "test-value"}],
    )

    # Assert
    assert task_arn == "arn:aws:ecs:region::task/task-id"

    mock_ecs_client.run_task.assert_called_once_with(
        taskDefinition="test-task-def",
        cluster="my-cluster",
        capacityProviderStrategy=[{"capacityProvider": "FARGATE", "weight": 1, "base": 0}],
        enableExecuteCommand=True,
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": ["public-subnet"],
                "securityGroups": ["security-group"],
                "assignPublicIp": "ENABLED",
            }
        },
        overrides={
            "containerOverrides": [
                {
                    "name": "test-container",
                    "environment": [{"name": "TEST_VAR", "value": "test-value"}],
                }
            ]
        },
    )


def test_exec_task_uses_retry_decorator():
    ecs = ECS(MagicMock(), MagicMock(), "myapp", "development")

    mock_suprocess = MagicMock(return_value=0)

    ecs.exec_task("cluster-arn", "task-arn", mock_suprocess)

    assert ecs.exec_task.__wrapped_by__ == "retry"
    mock_suprocess.assert_called()


def test_exec_task_raises_platform_exception():
    ecs = ECS(MagicMock(), MagicMock(), "myapp", "development")

    mock_suprocess = MagicMock(return_value=1)

    with pytest.raises(
        PlatformException,
        match="Failed to exec into ECS task.",
    ):
        ecs.exec_task("cluster-arn", "task-arn", mock_suprocess)

    assert ecs.exec_task.__wrapped_by__ == "retry"
    mock_suprocess.assert_called()
