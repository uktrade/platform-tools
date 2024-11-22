import boto3
import pytest
from moto import mock_aws

from dbt_platform_helper.exceptions import NoClusterError
from dbt_platform_helper.providers.ecs import addon_client_is_running
from dbt_platform_helper.providers.ecs import check_if_ecs_exec_is_available
from dbt_platform_helper.providers.ecs import get_cluster_arn
from dbt_platform_helper.providers.ecs import get_or_create_task_name
from tests.platform_helper.conftest import mock_parameter_name
from tests.platform_helper.conftest import mock_task_name

env = "development"


@mock_aws
def test_get_cluster_arn(mocked_cluster, mock_application):
    """Test that, given app and environment strings, get_cluster_arn returns the
    arn of a cluster tagged with these strings."""

    assert (
        get_cluster_arn(
            mock_application.environments[env].session.client("ecs"), mock_application.name, env
        )
        == mocked_cluster["cluster"]["clusterArn"]
    )


@mock_aws
def test_get_cluster_arn_when_there_is_no_cluster(mock_application):
    """Test that, given app and environment strings, get_cluster_arn raises an
    exception when no cluster tagged with these strings exists."""

    env = "staging"

    with pytest.raises(NoClusterError):
        get_cluster_arn(
            mock_application.environments[env].session.client("ecs"), mock_application.name, env
        )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_addon_client_is_running(
    mock_cluster_client_task, mocked_cluster, addon_type, mock_application
):
    """Test that, given cluster ARN, addon type and with a running agent,
    addon_client_is_running returns True."""

    mock_cluster_client_task(addon_type)
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    ecs_client = mock_application.environments[env].session.client("ecs")

    assert addon_client_is_running(ecs_client, mocked_cluster_arn, mock_task_name(addon_type))


@pytest.mark.parametrize(
    "addon_type",
    ["postgres"],  # , "redis", "opensearch"
)
def test_addon_client_and_exec_is_running(
    mock_cluster_client_task, mocked_cluster, addon_type, mock_application
):
    """Test that, given cluster ARN, addon type and with a running agent,
    addon_client_is_running returns True."""

    # use mock ecs_client as describe_tasks is overriden
    mocked_ecs_client = mock_cluster_client_task(addon_type)
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]

    assert (
        check_if_ecs_exec_is_available(
            mocked_ecs_client,
            mocked_cluster_arn,
            ["arn:aws:ecs:eu-west-2:12345678:task/does-not-matter/1234qwer"],
        )
        is "RUNNING"
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_addon_client_and_exec_is_not_running(
    mock_cluster_client_task, mocked_cluster, addon_type, mock_application
):
    """Test that, given cluster ARN, addon type and with a running agent,
    addon_client_is_running returns True."""

    # TODO UNKNOWN is not a real status here find it and use that, using UNKNOWN as we are just checking if the value is not RUNNING
    mocked_ecs_client = mock_cluster_client_task(addon_type, "PENDING")
    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]

    assert (
        check_if_ecs_exec_is_available(
            mocked_ecs_client,
            mocked_cluster_arn,
            ["arn:aws:ecs:eu-west-2:12345678:task/does-not-matter/1234qwer"],
        )
        is "PENDING"
    )


@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_addon_client_is_running_when_no_client_task_running(
    mocked_cluster, addon_type, mock_application
):
    """Test that, given cluster ARN, addon type and without a running client
    task, addon_client_is_running returns False."""

    mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    ecs_client = mock_application.environments[env].session.client("ecs")

    assert (
        len(addon_client_is_running(ecs_client, mocked_cluster_arn, mock_task_name(addon_type)))
        is 0
    )


@mock_aws
@pytest.mark.parametrize(
    "addon_type",
    ["postgres", "redis", "opensearch"],
)
def test_addon_client_is_running_when_no_client_agent_running(
    addon_type, mock_application, mocked_cluster
):
    ecs_client = mock_application.environments[env].session.client("ecs")
    cluster_arn = mocked_cluster["cluster"]["clusterArn"]
    task_name = "some-task-name"
    ec2 = boto3.resource("ec2")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/18")

    mocked_task_definition_arn = ecs_client.register_task_definition(
        family=f"copilot-foobar",
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

    assert len(addon_client_is_running(ecs_client, cluster_arn, task_name)) is 0


@mock_aws
def test_get_or_create_task_name(mock_application):
    """Test that get_or_create_task_name retrieves the task name from the
    parameter store when it has been stored."""

    addon_name = "app-postgres"
    parameter_name = mock_parameter_name(mock_application, "postgres", addon_name)
    mock_application.environments[env].session.client("ssm")
    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name=parameter_name,
        Type="String",
        Value=mock_task_name(addon_name),
    )

    task_name = get_or_create_task_name(
        mock_ssm, mock_application.name, env, addon_name, parameter_name
    )

    assert task_name == mock_task_name(addon_name)


@mock_aws
def test_get_or_create_task_name_when_name_does_not_exist(mock_application):
    """Test that get_or_create_task_name creates the task name and appends it
    with a 12 digit lowercase alphanumeric string when it does not exist in the
    parameter store."""

    addon_name = "app-postgres"
    ssm_client = mock_application.environments[env].session.client("ssm")
    parameter_name = mock_parameter_name(mock_application, "postgres", addon_name)
    task_name = get_or_create_task_name(
        ssm_client, mock_application.name, env, addon_name, parameter_name
    )
    random_id = task_name.rsplit("-", 1)[1]

    assert task_name.rsplit("-", 1)[0] == mock_task_name("app-postgres").rsplit("-", 1)[0]
    assert random_id.isalnum() and random_id.islower() and len(random_id) == 12
