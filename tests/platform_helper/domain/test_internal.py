import json
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from dbt_platform_helper.domain.internal import Internal
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import Environment


class InternalMocks:
    def __init__(self, app_name="myapp", env_name="dev", account_id="111122223333"):
        self.ecs_provider = Mock()
        self.loader = Mock()
        self.s3_provider = Mock()
        self.logs_provider = Mock()

        # Fake Application object
        env = Environment(name=env_name, account_id=account_id, sessions={})
        self.application = Application(name=app_name, environments={env_name: env})
        self.load_application = Mock(return_value=self.application)

    def params(self):
        return dict(
            ecs_provider=self.ecs_provider,
            load_application=self.load_application,
            loader=self.loader,
            s3_provider=self.s3_provider,
            logs_provider=self.logs_provider,
        )


def get_ecs_update_service_response(service_name="myapp-dev-web", deployment_id="dep-123"):
    return {
        "serviceName": service_name,
        "deployments": [
            {"id": "old-deployment", "status": "ACTIVE"},
            {"id": deployment_id, "status": "PRIMARY"},
        ],
    }


@patch("dbt_platform_helper.domain.internal.YamlFileProvider")
def test_deploy_happy_path_uses_override_tag(yaml_file_provider):
    mocks = InternalMocks()
    internal = Internal(**mocks.params())

    yaml_file_provider.load.return_value = {"name": "web", "count": 2}
    svc_model = Mock()
    svc_model.name = "web"
    svc_model.count = 2

    mocks.loader.load_into_model.return_value = svc_model

    mocks.s3_provider.get_object.return_value = json.dumps({"containerDefinitions": "FAKE"})

    mocks.ecs_provider.register_task_definition.return_value = (
        "arn:aws:ecs:eu-west-2:111122223333:task-definition/myapp-dev-web-task-def:999"
    )
    mocks.ecs_provider.update_service.return_value = get_ecs_update_service_response(
        service_name="myapp-dev-web", deployment_id="dep-abc"
    )
    mocks.ecs_provider.get_container_names_from_ecs_tasks.return_value = ["web", "datadog"]

    # Skip waiting for time loops in those methods to reach timeout
    with patch.object(
        internal, "_fetch_ecs_task_ids", return_value=["task1", "task2"]
    ) as ecs_task_ids, patch.object(
        internal, "_monitor_ecs_deployment", return_value=True
    ) as monitor_ecs_deployment:

        internal.deploy(
            service="web",
            environment="dev",
            application="myapp",
            image_tag_override="tag-123",
        )

    yaml_file_provider.load.assert_called_once_with("terraform/services/dev/web/service-config.yml")
    mocks.loader.load_into_model.assert_called_once()

    mocks.s3_provider.get_object.assert_called_once_with(
        bucket_name="ecs-container-definitions-myapp-dev",
        object_key="myapp/dev/web.json",
    )

    kwargs = mocks.ecs_provider.register_task_definition.call_args.kwargs
    assert kwargs == dict(
        service_model=svc_model,
        environment="dev",
        application="myapp",
        image_tag="tag-123",
        account_id="111122223333",
        container_definitions={"containerDefinitions": "FAKE"},
    )

    mocks.ecs_provider.update_service.assert_called_once_with(
        svc_model,
        "arn:aws:ecs:eu-west-2:111122223333:task-definition/myapp-dev-web-task-def:999",
        "dev",
        "myapp",
    )

    ecs_task_ids.assert_called_once_with(
        application="myapp",
        environment="dev",
        service_model=svc_model,
        service_response=mocks.ecs_provider.update_service.return_value,
    )
    mocks.ecs_provider.get_container_names_from_ecs_tasks.assert_called_once_with(
        cluster_name="myapp-dev-cluster",
        task_ids=["task1", "task2"],
    )
    monitor_ecs_deployment.assert_called_once_with(
        application="myapp",
        environment="dev",
        service="web",
        log_streams=[
            "platform/web/task1",
            "platform/datadog/task1",
            "platform/web/task2",
            "platform/datadog/task2",
        ],
    )


@patch("dbt_platform_helper.domain.internal.EnvironmentVariableProvider")
@patch("dbt_platform_helper.domain.internal.YamlFileProvider")
def test_deploy_uses_env_var_if_no_override(yaml_file_provider, env_var_provider):
    env_var_provider.get.return_value = "tag-123"
    mocks = InternalMocks()
    internal = Internal(**mocks.params())

    yaml_file_provider.load.return_value = {"name": "web", "count": 1}
    svc_model = Mock()
    svc_model.name = "web"
    svc_model.count = 1

    mocks.loader.load_into_model.return_value = svc_model

    mocks.s3_provider.get_object.return_value = json.dumps({})
    mocks.ecs_provider.register_task_definition.return_value = (
        "arn:aws:ecs:eu-west-2:111122223333:task-definition/myapp-dev-web-task-def:999"
    )
    mocks.ecs_provider.update_service.return_value = get_ecs_update_service_response()

    mocks.ecs_provider.get_container_names_from_ecs_tasks.return_value = ["web", "datadog"]

    # Skip waiting for the time-based loops in those methods to reach their timeouts
    with patch.object(internal, "_fetch_ecs_task_ids", return_value=["task1"]), patch.object(
        internal, "_monitor_ecs_deployment", return_value=True
    ):
        internal.deploy(service="web", environment="dev", application="myapp")

    assert mocks.ecs_provider.register_task_definition.call_args.kwargs["image_tag"] == "tag-123"


@patch("dbt_platform_helper.domain.internal.time.sleep", return_value=None)
def test_fetch_ecs_task_ids_success(time_sleep):
    mocks = InternalMocks()
    internal = Internal(**mocks.params())
    svc_model = Mock()
    svc_model.name = "web"
    svc_model.count = 2

    mocks.ecs_provider.get_ecs_task_arns.return_value = [
        "arn:aws:ecs:eu-west-2:111122223333:task/myapp-dev-cluster/task1",
        "arn:aws:ecs:eu-west-2:111122223333:task/myapp-dev-cluster/task2",
    ]

    task_ids = internal._fetch_ecs_task_ids(
        application="myapp",
        environment="dev",
        service_model=svc_model,
        service_response=get_ecs_update_service_response(deployment_id="deployment-id"),
    )

    assert task_ids == ["task1", "task2"]

    mocks.ecs_provider.get_ecs_task_arns.assert_called_once_with(
        cluster="myapp-dev-cluster",
        started_by="deployment-id",
        desired_status="RUNNING",
    )


def test_fetch_ecs_task_ids_no_primary_deployment():
    mocks = InternalMocks()
    internal = Internal(**mocks.params())
    svc_model = Mock()
    svc_model.name = "web"
    svc_model.count = 1

    ecs_response_with_wrong_deployment = {
        "serviceName": "svc",
        "deployments": [{"id": "deployment-id", "status": "INACTIVE"}],
    }
    with pytest.raises(PlatformException) as e:
        internal._fetch_ecs_task_ids("myapp", "dev", svc_model, ecs_response_with_wrong_deployment)
    assert "Unable to find primary ECS deployment" in str(e.value)


@patch("dbt_platform_helper.domain.internal.time.sleep", return_value=None)
def test_fetch_ecs_task_ids_times_out(time_sleep):
    mocks = InternalMocks()
    internal = Internal(**mocks.params())
    svc_model = Mock()
    svc_model.name = "web"
    svc_model.count = 3

    # One task returned instead of 3
    mocks.ecs_provider.get_ecs_task_arns.return_value = [
        "arn:aws:ecs:eu-west-2:111122223333:task/myapp-dev-cluster/task1234"
    ]

    # Fake time: 0 = deadline starts, 1 = loop once, 601 = timeout and exit
    with patch("dbt_platform_helper.domain.internal.time.monotonic", side_effect=[0, 1, 601]):
        with pytest.raises(PlatformException) as e:
            internal._fetch_ecs_task_ids(
                "myapp",
                "dev",
                svc_model,
                get_ecs_update_service_response("myapp-dev-web", "deployment-id"),
            )

    assert "Timed out waiting for 3 RUNNING ECS task(s)" in str(e.value)


@patch("dbt_platform_helper.domain.internal.time.sleep", return_value=None)
def test_monitor_ecs_deployment_completed(time_sleep):
    mocks = InternalMocks()
    internal = Internal(**mocks.params())

    mocks.logs_provider.filter_log_events.return_value = {"events": []}
    mocks.ecs_provider.get_service_rollout_state.return_value = ("COMPLETED", None)

    # Fake time: 0 = deadline starts, 1 = loop once
    with patch("dbt_platform_helper.domain.internal.time.monotonic", side_effect=[0, 1]):
        deployment_success = internal._monitor_ecs_deployment(
            "myapp", "dev", "web", ["platform/web/task1234"]
        )
    assert deployment_success is True


@patch("dbt_platform_helper.domain.internal.time.sleep", return_value=None)
def test_monitor_ecs_deployment_failed(time_sleep):
    mocks = InternalMocks()
    internal = Internal(**mocks.params())

    mocks.logs_provider.filter_log_events.return_value = {"events": []}
    mocks.ecs_provider.get_service_rollout_state.return_value = ("FAILED", "There was an error")

    # Fake time: 0 = deadline starts, 1 = loop once
    with patch("dbt_platform_helper.domain.internal.time.monotonic", side_effect=[0, 1]):
        with pytest.raises(PlatformException) as e:
            internal._monitor_ecs_deployment("myapp", "dev", "web", ["platform/web/task1234"])
    assert "ECS deployment failed: There was an error" in str(e.value)


@patch("dbt_platform_helper.domain.internal.time.sleep", return_value=None)
def test_monitor_ecs_deployment_raises_exception(time_sleep):
    mocks = InternalMocks()
    internal = Internal(**mocks.params())

    mocks.logs_provider.filter_log_events.return_value = {"events": []}
    mocks.ecs_provider.get_service_rollout_state.side_effect = Exception("An exception")

    # Fake time: 0 = deadline starts, 1 = loop once
    with patch("dbt_platform_helper.domain.internal.time.monotonic", side_effect=[0, 1]):
        with pytest.raises(PlatformException) as e:
            internal._monitor_ecs_deployment("myapp", "dev", "web", ["platform/web/task1234"])
    assert "Failed to fetch ECS rollout state: An exception" in str(e.value)
