import time
from unittest.mock import MagicMock
from unittest.mock import patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.providers.ecs import NoClusterException
from dbt_platform_helper.providers.vpc import Vpc
from dbt_platform_helper.utilities.decorators import RetryException
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

    ecs_manager = ECS(ecs_client, ssm_client, application_name="myapp", env="development")

    with pytest.raises(NoClusterException):
        ecs_manager.get_cluster_arn_by_copilot_tag()

    ecs_client.list_clusters.assert_called_once()


def test_get_cluster_arn_with_no_cluster_raises_error():
    ecs_client = MagicMock()
    ssm_client = MagicMock()

    ecs_client.describe_clusters.return_value = {"clusters": []}

    ecs_manager = ECS(ecs_client, ssm_client, application_name="myapp", env="development")

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

    ecs = ECS(ecs_client, ssm_client, "myapp", "development")

    with pytest.raises(NoClusterException):
        ecs.get_cluster_arn_by_name("some-cluster")

    ecs_client.describe_clusters.assert_called_once_with(clusters=["some-cluster"])


def test_get_cluster_arn_by_name_missing_arn_raises():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.describe_clusters.return_value = {"clusters": [{}]}  # Without 'clusterArn' field

    ecs = ECS(ecs_client, ssm_client, "myapp", "development")

    with pytest.raises(NoClusterException):
        ecs.get_cluster_arn_by_name("some-cluster")


def test_get_cluster_arn_by_name_passes_correct_cluster():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.describe_clusters.return_value = {"clusters": [{"clusterArn": "arn:cluster"}]}

    ecs = ECS(ecs_client, ssm_client, "myapp", "development")
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
        cluster=mocked_cluster_arn, task_def_family=f"copilot-{mock_task_name(addon_type)}"
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
    assert (
        len(
            ecs_manager.get_ecs_task_arns(
                cluster=mocked_cluster_arn, task_def_family=mock_task_name(addon_type)
            )
        )
        == 0
    )


@mock_aws
def test_get_ecs_task_arns_does_not_return_arns_from_other_tasks(mock_application, mocked_cluster):
    ecs_client = mock_application.environments["development"].session.client("ecs")
    ec2_client = mock_application.environments["development"].session.client("ec2")
    cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    task_name = "no-running-task"
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    ec2_client.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={"Value": True})
    subnet = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock="10.0.0.0/18")
    subnet_id = subnet["Subnet"]["SubnetId"]
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
                "subnets": [subnet_id],
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
    assert len(ecs_manager.get_ecs_task_arns(cluster=cluster_arn, task_def_family=task_name)) == 0


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


@mock_aws
def test_ecs_exec_is_available_with_exec_not_running_raises_exception(
    mock_cluster_client_task, mocked_cluster, mock_application
):
    mocked_ecs_client = mock_cluster_client_task("postgres", "PENDING")
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    ecs_manager = ECS(
        mocked_ecs_client,
        mock_application.environments["development"].session.client("ssm"),
        mock_application.name,
        "development",
    )
    with patch("time.sleep", return_value=None):
        with pytest.raises(RetryException, match="ECS Agent Not running") as actual_exec:
            ecs_manager.ecs_exec_is_available(
                mocked_cluster_arn, ["arn:aws:ecs:eu-west-2:12345678:task/does-not-matter/1234qwer"]
            )
    assert "ecs_exec_is_available" in str(actual_exec.value)
    assert "25 attempts" in str(actual_exec.value)
    assert "ECS Agent Not running" in str(actual_exec.value)


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


def test_get_ecs_task_arns_returns_arns():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.list_tasks.return_value = {"taskArns": ["arn1", "arn2"]}

    ecs = ECS(ecs_client, ssm_client, "myapp", "dev")

    arns = ecs.get_ecs_task_arns(
        cluster="myapp-cluster",
        max_results=50,
        desired_status="RUNNING",
        service_name="myapp-dev-web",
        started_by="deployment-123",
        task_def_family="my-task-def-family",
    )

    assert arns == ["arn1", "arn2"]
    ecs_client.list_tasks.assert_called_once_with(
        cluster="myapp-cluster",
        maxResults=50,
        desiredStatus="RUNNING",
        serviceName="myapp-dev-web",
        startedBy="deployment-123",
        family="my-task-def-family",
    )


def test_get_service_deployment_state_success():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.list_service_deployments.return_value = {
        "serviceDeployments": [{"status": "SUCCESSFUL"}]
    }
    start_time = time.time()
    ecs = ECS(ecs_client, ssm_client, "myapp", "dev")
    state, reason = ecs.get_service_deployment_state(
        "myapp-dev-cluster", "myapp-dev-web", start_time=start_time
    )
    assert state == "SUCCESSFUL"
    assert reason is None
    ecs_client.list_service_deployments.assert_called_once_with(
        cluster="myapp-dev-cluster", service="myapp-dev-web", createdAt={"after": start_time}
    )


def test_get_service_deployment_state_failed():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.list_service_deployments.return_value = {
        "serviceDeployments": [{"status": "FAILED", "statusReason": "Some error occurred"}]
    }
    ecs = ECS(ecs_client, ssm_client, "myapp", "dev")
    assert ecs.get_service_deployment_state("cluster", "service", start_time=time.time()) == (
        "FAILED",
        "Some error occurred",
    )


def test_get_service_deployment_state_service_not_found():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.list_service_deployments.return_value = {"serviceDeployments": []}
    ecs = ECS(ecs_client, ssm_client, "myapp", "dev")
    assert ecs.get_service_deployment_state(
        "cluster", "non-existent-service", start_time=time.time()
    ) == (
        None,
        "No deployments found for 'non-existent-service'",
    )


def test_get_container_names_from_ecs_tasks():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.describe_tasks.return_value = {
        "tasks": [
            {"containers": [{"name": "web"}, {"name": "ip-filter"}]},
            {"containers": [{"name": "web"}, {"name": "datadog"}]},
        ]
    }
    ecs = ECS(ecs_client, ssm_client, "myapp", "dev")
    names = ecs.get_container_names_from_ecs_tasks("cluster", ["task1", "task2"])
    assert names == ["web", "ip-filter", "datadog"]
    ecs_client.describe_tasks.assert_called_once_with(cluster="cluster", tasks=["task1", "task2"])


def _client_error(operation="RegisterTaskDefinition"):
    return ClientError(
        error_response={"Error": {"Code": "SomeErrorCode", "Message": "Some error took place"}},
        operation_name=operation,
    )


def test_register_task_definition_applies_image_tag_override():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.register_task_definition.return_value = {
        "taskDefinition": {"taskDefinitionArn": "arn:taskdef:123"}
    }

    task_definition = {
        "family": "doesn't matter",
        "other parameters...": "they also don't matter",
        "containerDefinitions": [
            {
                "name": "web",
                "image": "111122223333.dkr.ecr.eu-west-2.amazonaws.com/myapp/web:old-image-tag",
            },
            {"name": "sidecar", "image": "sidecar:v1.2.3"},
        ],
    }

    ecs = ECS(ecs_client, ssm_client, "myapp", "dev")
    arn = ecs.register_task_definition(
        service="web",
        task_definition=task_definition,
        image_tag="new-image-tag",
    )

    assert arn == "arn:taskdef:123"
    # Image tag is rewritten only for the main container
    assert (
        task_definition["containerDefinitions"][0]["image"]
        == "111122223333.dkr.ecr.eu-west-2.amazonaws.com/myapp/web:new-image-tag"
    )
    assert task_definition["containerDefinitions"][1]["image"] == "sidecar:v1.2.3"

    ecs_client.register_task_definition.assert_called_once()
    kwargs = ecs_client.register_task_definition.call_args.kwargs
    assert kwargs["containerDefinitions"] is task_definition["containerDefinitions"]


def test_register_task_definition_raises_exception():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.register_task_definition.side_effect = _client_error("RegisterTaskDefinition")

    ecs = ECS(ecs_client, ssm_client, "myapp", "dev")

    task_definition = {
        "family": "doesn't matter",
        "other parameters...": "they also don't matter",
        "containerDefinitions": [
            {"name": "web", "image": "web:tag-latest"},
            {"name": "sidecar", "image": "sidecar:tag-1.2.3"},
        ],
    }

    with pytest.raises(PlatformException) as e:
        ecs.register_task_definition(
            service="web",
            task_definition=task_definition,
            image_tag="tag",
        )
    assert "Error registering task definition" in str(e.value)


def test_update_service_success():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.update_service.return_value = {"service": {"serviceName": "myapp-dev-web"}}

    ecs = ECS(ecs_client, ssm_client, "myapp", "dev")
    svc = ecs.update_service(
        service="web",
        task_def_arn="arn:taskdef:1",
        environment="dev",
        application="myapp",
        desired_count=1,
    )

    assert svc == {"serviceName": "myapp-dev-web"}
    ecs_client.update_service.assert_called_once_with(
        cluster="myapp-dev-cluster",
        service="myapp-dev-web",
        taskDefinition="arn:taskdef:1",
        desiredCount=1,
    )


def test_update_service_raises_exception():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.update_service.side_effect = _client_error("UpdateService")

    service_model = MagicMock()
    service_model.name = "web"
    service_model.count = 1

    ecs = ECS(ecs_client, ssm_client, "myapp", "dev")
    with pytest.raises(PlatformException) as e:
        ecs.update_service(service_model, "arn:taskdef:1", "dev", "myapp", desired_count=1)
    assert "Error updating ECS service" in str(e.value)


@patch("time.sleep", return_value=None)
def test_wait_for_task_to_register(time_sleep):
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs = ECS(ecs_client, ssm_client, "myapp", "dev")

    # Returns task arn on third attempt
    ecs.get_ecs_task_arns = MagicMock(side_effect=[[], [], ["arn1"]])

    result = ecs.wait_for_task_to_register("cluster-arn", "task-def-family")
    assert result == ["arn1"]


def test_describe_service_success():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.describe_services.return_value = {"services": [{"serviceName": "myapp-dev-web"}]}

    ecs = ECS(ecs_client, ssm_client, "myapp", "dev")
    svc = ecs.describe_service(service="web", environment="dev", application="myapp")

    assert svc == {"serviceName": "myapp-dev-web"}
    ecs_client.describe_services.assert_called_once_with(
        cluster="myapp-dev-cluster", services=["myapp-dev-web"]
    )


def test_describe_tasks_success():
    ecs_client = MagicMock()
    ssm_client = MagicMock()
    ecs_client.describe_tasks.return_value = {
        "tasks": [{"taskArn": "arn:aws:ecs:eu-west-2:123456789:task/myapp-dev-cluster/abc123"}]
    }

    ecs = ECS(ecs_client, ssm_client, "myapp", "dev")
    tasks = ecs.describe_tasks(cluster_name="myapp-dev-cluster", task_ids=["abc123"])

    assert tasks == [{"taskArn": "arn:aws:ecs:eu-west-2:123456789:task/myapp-dev-cluster/abc123"}]
    ecs_client.describe_tasks.assert_called_once_with(cluster="myapp-dev-cluster", tasks=["abc123"])
