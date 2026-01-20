import json
import os
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

import pytest
import yaml
from freezegun import freeze_time

from dbt_platform_helper.domain.service import ServiceManager
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import Environment


@pytest.fixture
def copilot_manifest(tmp_path):
    copilot_dir = tmp_path / "copilot" / "my-service"
    copilot_dir.mkdir(parents=True)
    manifest_path = copilot_dir / "manifest.yml"
    manifest_content = {
        "name": "my-service",
        "type": "Load Balanced Web Service",
        "environments": {
            "dev": {"http": {"alb": "alb-arn", "alias": "test.alias.com"}},
            "prod": {"http": {"alb": "alb-arn", "alias": ["test.alias.com", "test2.alias.com"]}},
        },
        "variables": {"S3_BUCKET_NAME": "${COPILOT_APPLICATION_NAME}-${COPILOT_ENVIRONMENT_NAME}"},
    }
    with open(manifest_path, "w") as f:
        yaml.safe_dump(manifest_content, f)
    return tmp_path


def test_migrate_copilot_manifests_creates_services_directory_and_files(tmp_path, copilot_manifest):
    output_dir = tmp_path / "services"
    file_path = output_dir / "my-service/service-config.yml"

    os.chdir(tmp_path)
    service_manager = ServiceManager()
    service_manager.migrate_copilot_manifests()

    assert file_path.exists()


def test_migrate_copilot_manifests_generates_expected_service_config(tmp_path, copilot_manifest):
    expected_service_config = {
        "name": "my-service",
        "type": "Load Balanced Web Service",
        "environments": {
            "dev": {"http": {"alias": ["test.alias.com"]}},
            "prod": {"http": {"alias": ["test.alias.com", "test2.alias.com"]}},
        },
        "variables": {
            "S3_BUCKET_NAME": "${PLATFORM_APPLICATION_NAME}-${PLATFORM_ENVIRONMENT_NAME}"
        },
    }

    os.chdir(tmp_path)
    service_manager = ServiceManager()
    service_manager.migrate_copilot_manifests()

    with open(tmp_path / "services/my-service/service-config.yml") as f:
        service_config = yaml.safe_load(f)

    assert service_config == expected_service_config


def test_migrate_copilot_manifests_skips_unwanted_service_types(tmp_path):
    copilot_dir = tmp_path / "copilot" / "my-service"
    copilot_dir.mkdir(parents=True)
    manifest_path = copilot_dir / "manifest.yml"
    manifest_content = {"name": "my-service", "type": "Scheduled Job"}
    with open(manifest_path, "w") as f:
        yaml.safe_dump(manifest_content, f)

    output_dir = tmp_path / "services"
    file_path = output_dir / "my-service/service-config.yml"

    os.chdir(tmp_path)
    service_manager = ServiceManager()
    service_manager.migrate_copilot_manifests()

    assert not file_path.exists()


def test_migrate_copilot_manifests_sets_depends_on_for_remaining_sidecars(
    tmp_path,
):
    copilot_dir = tmp_path / "copilot" / "my-service"
    copilot_dir.mkdir(parents=True)
    manifest_path = copilot_dir / "manifest.yml"

    manifest_content = {
        "name": "my-service",
        "type": "Load Balanced Web Service",
        "image": {"location": "myrepo/myimage:latest"},
        "sidecars": {
            "permissions": {
                "command": "chown -R 1000:1000 /tmp",
                "mount_points": [{"path": "/tmp"}],
            },
            "hello-world": {
                "command": 'echo "Hello World"',
            },
        },
    }

    with open(manifest_path, "w") as f:
        yaml.safe_dump(manifest_content, f)

    os.chdir(tmp_path)
    service_manager = ServiceManager()

    service_manager.migrate_copilot_manifests()

    with open(tmp_path / "services/my-service/service-config.yml") as f:
        service_config = yaml.safe_load(f)

    assert "sidecars" in service_config
    assert "permissions" not in service_config["sidecars"]
    assert "hello-world" in service_config["sidecars"]

    assert service_config["image"]["depends_on"] == {"hello-world": "start"}


class ServiceManagerMocks:
    def __init__(self, app_name="myapp", env_name="dev", account_id="111122223333"):
        self.ecs_provider = Mock()
        self.s3_provider = Mock()
        self.logs_provider = Mock()
        self.autoscaling_provider = Mock()
        self.io = Mock()

        # Fake Application object
        env = Environment(name=env_name, account_id=account_id, sessions={})
        self.application = Application(name=app_name, environments={env_name: env})
        self.load_application = Mock(return_value=self.application)

    def params(self):
        return dict(
            ecs_provider=self.ecs_provider,
            load_application=self.load_application,
            s3_provider=self.s3_provider,
            logs_provider=self.logs_provider,
            autoscaling_provider=self.autoscaling_provider,
            io=self.io,
        )


def get_ecs_update_service_response(
    service_name="myapp-dev-web", deployment_id="deployment-abc", events=None
):
    return {
        "serviceName": service_name,
        "deployments": [
            {"id": "old-deployment", "status": "ACTIVE"},
            {"id": deployment_id, "status": "PRIMARY"},
        ],
        "events": events or [],
    }


def get_ecs_task_response(exit_code: int = 0):
    return [
        {
            "taskArn": "arn:aws:ecs:eu-west-2:1234567890:task/myapp-dev-cluster/123abc",
            "containers": [{"name": "web", "exitCode": exit_code}],
        }
    ]


@freeze_time("2025-01-16 13:00:00")
def test_service_deploy_success():
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())

    mocks.s3_provider.get_object.return_value = json.dumps({"fakeTaskDefinition": "FAKE"})

    mocks.ecs_provider.register_task_definition.return_value = (
        "arn:aws:ecs:eu-west-2:111122223333:task-definition/myapp-dev-web-task-def:999"
    )

    update_service_response = get_ecs_update_service_response(
        service_name="myapp-dev-web", deployment_id="deployment-123"
    )
    mocks.ecs_provider.update_service.return_value = update_service_response
    mocks.ecs_provider.describe_service.return_value = update_service_response
    mocks.autoscaling_provider.describe_autoscaling_target.return_value = {"MinCapacity": 1}

    # Skip waiting for time loops in those methods to reach timeout
    with patch.object(
        service_manager, "_wait_for_new_tasks", return_value=["task1", "task2"]
    ) as wait_for_new_tasks, patch.object(
        service_manager, "_monitor_task_events"
    ) as monitor_task_events, patch.object(
        service_manager, "_monitor_service_events"
    ) as monitor_service_events:

        ecs_task_response = get_ecs_task_response()
        mocks.ecs_provider.describe_tasks.return_value = ecs_task_response
        mocks.ecs_provider.get_service_deployment_state.return_value = ("SUCCESSFUL", None)

        service_manager.deploy(
            service="web",
            environment="dev",
            application="myapp",
            image_tag="tag-123",
        )

    mocks.s3_provider.get_object.assert_called_once_with(
        bucket_name="ecs-task-definitions-myapp-dev",
        object_key="myapp/dev/web.json",
    )

    register_task_def_kwargs = mocks.ecs_provider.register_task_definition.call_args.kwargs
    assert register_task_def_kwargs["service"] == "web"
    assert register_task_def_kwargs["image_tag"] == "tag-123"
    assert register_task_def_kwargs["task_definition"] == {"fakeTaskDefinition": "FAKE"}

    describe_autoscaling_target_kwargs = (
        mocks.autoscaling_provider.describe_autoscaling_target.call_args.kwargs
    )
    assert describe_autoscaling_target_kwargs["cluster_name"] == "myapp-dev-cluster"
    assert describe_autoscaling_target_kwargs["ecs_service_name"] == "myapp-dev-web"

    update_service_kwargs = mocks.ecs_provider.update_service.call_args.kwargs
    assert update_service_kwargs["service"] == "web"
    assert (
        update_service_kwargs["task_def_arn"]
        == "arn:aws:ecs:eu-west-2:111122223333:task-definition/myapp-dev-web-task-def:999"
    )
    assert update_service_kwargs["environment"] == "dev"
    assert update_service_kwargs["application"] == "myapp"
    assert update_service_kwargs["desired_count"] == 1

    fetch_task_ids_kwargs = wait_for_new_tasks.call_args.kwargs
    assert fetch_task_ids_kwargs["cluster_name"] == "myapp-dev-cluster"
    assert fetch_task_ids_kwargs["deployment_id"] == "deployment-123"

    monitor_service_events.assert_called_once_with(
        service_response=update_service_response,
        seen_events=set(),
        start_time=datetime.now(timezone.utc),
    )

    monitor_task_events.assert_called_once_with(
        task_response=ecs_task_response,
        seen_events=set(),
        log_group="/platform/ecs/service/myapp/dev/web",
    )


@patch("dbt_platform_helper.domain.service.time.sleep", return_value=None)
def test_wait_for_new_tasks_success(time_sleep):
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())

    mocks.ecs_provider.get_ecs_task_arns.return_value = [
        "arn:aws:ecs:eu-west-2:111122223333:task/myapp-dev-cluster/task1",
        "arn:aws:ecs:eu-west-2:111122223333:task/myapp-dev-cluster/task2",
    ]

    task_ids = service_manager._wait_for_new_tasks(
        cluster_name="myapp-dev-cluster",
        deployment_id="deployment-id",
    )

    assert task_ids == ["task1", "task2"]

    mocks.ecs_provider.get_ecs_task_arns.assert_called_once_with(
        cluster="myapp-dev-cluster",
        started_by="deployment-id",
        desired_status="RUNNING",
    )


def test_get_primary_deployment_id_success():
    service_manager = ServiceManager()
    resp = get_ecs_update_service_response(service_name="svc", deployment_id="deployment-123")
    assert service_manager._get_primary_deployment_id(resp) == "deployment-123"


def test_get_primary_deployment_id_raises_exception():
    service_manager = ServiceManager()
    ecs_response_with_wrong_deployment = {
        "serviceName": "svc",
        "deployments": [{"id": "deployment-id", "status": "INACTIVE"}],
    }
    with pytest.raises(PlatformException) as e:
        service_manager._get_primary_deployment_id(ecs_response_with_wrong_deployment)
    assert "Unable to find primary ECS deployment" in str(e.value)


@patch("dbt_platform_helper.domain.service.time.sleep", return_value=None)
def test_wait_for_new_tasks_times_out(time_sleep):
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())

    # One task is returned instead of the 3 tasks expected
    mocks.ecs_provider.get_ecs_task_arns.return_value = []

    # Fake time: 0 = deadline starts, 1 = loop once, 601 = timeout and exit
    with patch("dbt_platform_helper.domain.service.time.monotonic", side_effect=[0, 1, 601]):
        with pytest.raises(PlatformException) as e:
            service_manager._wait_for_new_tasks(
                cluster_name="myapp-dev-cluster", deployment_id="deployment-id"
            )

    assert "Timed out waiting for RUNNING ECS tasks" in str(e.value)


@patch("dbt_platform_helper.domain.service.time.sleep", return_value=None)
def test_service_deploy_failed(time_sleep):
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())

    mocks.s3_provider.get_object.return_value = json.dumps({"fakeTaskDefinition": "FAKE"})
    mocks.ecs_provider.register_task_definition.return_value = (
        "arn:aws:ecs:eu-west-2:111122223333:task-definition/myapp-dev-web-task-def:999"
    )

    update_service_response = get_ecs_update_service_response(
        service_name="myapp-dev-web", deployment_id="deployment-123"
    )
    mocks.ecs_provider.update_service.return_value = update_service_response
    mocks.ecs_provider.describe_service.return_value = update_service_response

    # Skip waiting for time loops in those methods to reach timeout
    with patch.object(
        service_manager, "_wait_for_new_tasks", return_value=["task1", "task2"]
    ), patch.object(service_manager, "_monitor_task_events"):

        mocks.ecs_provider.describe_tasks.return_value = get_ecs_task_response()
        mocks.ecs_provider.get_service_deployment_state.return_value = (
            "ROLLBACK_SUCCESSFUL",
            "There was an error",
        )

        with pytest.raises(PlatformException) as e:
            service_manager.deploy(
                service="web",
                environment="dev",
                application="myapp",
                image_tag="tag-123",
            )
        assert "Deployment failed: There was an error" in str(e.value)


@freeze_time("2025-01-16 13:00:00")
def test_monitor_service_events_outputs_distinct_events():
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())

    service_response = get_ecs_update_service_response(
        service_name="myapp-dev-web",
        deployment_id="deployment-123",
        events=[
            {
                "id": "12345",
                "createdAt": datetime.now(timezone.utc),
                "message": "duplicate event message should be ignored.",
            },
            {
                "id": "12345",
                "createdAt": datetime.now(timezone.utc),
                "message": "(service myapp-dev-web) has started 1 tasks: (task abc123).",
            },
        ],
    )

    service_manager._monitor_service_events(
        service_response=service_response,
        seen_events=set(),
        start_time=datetime.now(timezone.utc) - timedelta(hours=1),
    )

    mocks.io.info.assert_called_once_with(
        "[13:00:00] (service myapp-dev-web) has started 1 tasks: (task abc123)."
    )


@freeze_time("2025-01-16 13:00:00")
def test_monitor_service_events_outputs_errors():
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())

    service_response = get_ecs_update_service_response(
        service_name="myapp-dev-web",
        deployment_id="deployment-123",
        events=[
            {
                "id": "12345",
                "createdAt": datetime.now(timezone.utc),
                "message": "Error task failed to start.",
            }
        ],
    )

    service_manager._monitor_service_events(
        service_response=service_response,
        seen_events=set(),
        start_time=datetime.now(timezone.utc) - timedelta(hours=1),
    )

    mocks.io.deploy_error.assert_called_once_with("[13:00:00] Error task failed to start.")


def test_monitor_task_events_success():
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())

    task_response = get_ecs_task_response(exit_code=1)
    log_group = "/platform/ecs/service/myapp/dev/web"

    mocks.logs_provider.get_log_stream_events.return_value = [{"message": "test"}]

    service_manager._monitor_task_events(
        task_response=task_response,
        seen_events=set(),
        log_group=log_group,
    )

    mocks.logs_provider.get_log_stream_events.assert_called_once_with(
        log_group=log_group,
        log_stream=f"platform/web/123abc",
        limit=20,
    )


@freeze_time("2025-01-16 13:00:00")
def test_monitor_task_events_outputs_events():
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())

    task_response = get_ecs_task_response(exit_code=1)
    log_group = "/platform/ecs/service/myapp/dev/web"

    mocks.logs_provider.get_log_stream_events.return_value = [{"message": "Application error"}]

    service_manager._monitor_task_events(
        task_response=task_response,
        seen_events=set(),
        log_group=log_group,
    )

    mocks.io.deploy_error.assert_has_calls(
        [
            call("[13:00:00] Container 'web' stopped in task '123abc'."),
            call(
                "[13:00:00] View CloudWatch log: https://eu-west-2.console.aws.amazon.com/cloudwatch/home?region=eu-west-2#logsV2:log-groups/log-group/%2Fplatform%2Fecs%2Fservice%2Fmyapp%2Fdev%2Fweb/log-events/platform%2Fweb%2F123abc"
            ),
            call("[13:00:00] Application error"),
        ]
    )
