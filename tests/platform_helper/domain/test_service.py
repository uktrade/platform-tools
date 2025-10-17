import json
import os
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml

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
        "environments": {"dev": {"http": {"alb": "alb-arn", "alias": "test.alias.com"}}},
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
        "environments": {"dev": {"http": {"alias": "test.alias.com"}}},
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


class ServiceManagerMocks:
    def __init__(self, app_name="myapp", env_name="dev", account_id="111122223333"):
        self.ecs_provider = Mock()
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
            s3_provider=self.s3_provider,
            logs_provider=self.logs_provider,
        )


def get_ecs_update_service_response(service_name="myapp-dev-web", deployment_id="deployment-abc"):
    return {
        "serviceName": service_name,
        "deployments": [
            {"id": "old-deployment", "status": "ACTIVE"},
            {"id": deployment_id, "status": "PRIMARY"},
        ],
    }


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
    update_service_response["desiredCount"] = 2
    mocks.ecs_provider.update_service.return_value = update_service_response

    mocks.ecs_provider.get_container_names_from_ecs_tasks.return_value = ["web", "datadog"]

    # Skip waiting for time loops in those methods to reach timeout
    with patch.object(
        service_manager, "_fetch_ecs_task_ids", return_value=["task1", "task2"]
    ) as fetch_ecs_task_ids, patch.object(
        service_manager, "_monitor_ecs_deployment", return_value=True
    ) as monitor_ecs_deployment:

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

    update_service_kwargs = mocks.ecs_provider.update_service.call_args.kwargs
    assert update_service_kwargs["service"] == "web"
    assert (
        update_service_kwargs["task_def_arn"]
        == "arn:aws:ecs:eu-west-2:111122223333:task-definition/myapp-dev-web-task-def:999"
    )
    assert update_service_kwargs["environment"] == "dev"
    assert update_service_kwargs["application"] == "myapp"

    fetch_task_ids_kwargs = fetch_ecs_task_ids.call_args.kwargs
    assert fetch_task_ids_kwargs["application"] == "myapp"
    assert fetch_task_ids_kwargs["environment"] == "dev"
    assert fetch_task_ids_kwargs["deployment_id"] == "deployment-123"
    assert fetch_task_ids_kwargs["expected_count"] == 2

    monitor_ecs_deployment.assert_called_once_with(
        application="myapp", environment="dev", service="web"
    )


@patch("dbt_platform_helper.domain.service.EnvironmentVariableProvider")
def test_deploy_success_uses_env_var(env_var_provider):
    env_var_provider.get.return_value = "tag-123"
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())

    mocks.s3_provider.get_object.return_value = json.dumps({})
    mocks.ecs_provider.register_task_definition.return_value = (
        "arn:aws:ecs:eu-west-2:111122223333:task-definition/myapp-dev-web-task-def:999"
    )

    update_service_response = get_ecs_update_service_response()
    update_service_response["desiredCount"] = 1
    mocks.ecs_provider.update_service.return_value = update_service_response

    mocks.ecs_provider.get_container_names_from_ecs_tasks.return_value = ["web", "datadog"]

    # Skip waiting for the time-based loops in those methods to reach their timeouts
    with patch.object(service_manager, "_fetch_ecs_task_ids", return_value=["task1"]), patch.object(
        service_manager, "_monitor_ecs_deployment", return_value=True
    ):
        service_manager.deploy(service="web", environment="dev", application="myapp")

    assert mocks.ecs_provider.register_task_definition.call_args.kwargs["image_tag"] == "tag-123"
    assert mocks.ecs_provider.register_task_definition.call_args.kwargs["service"] == "web"


@patch("dbt_platform_helper.domain.service.time.sleep", return_value=None)
def test_fetch_ecs_task_ids_success(time_sleep):
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())

    mocks.ecs_provider.get_ecs_task_arns.return_value = [
        "arn:aws:ecs:eu-west-2:111122223333:task/myapp-dev-cluster/task1",
        "arn:aws:ecs:eu-west-2:111122223333:task/myapp-dev-cluster/task2",
    ]

    task_ids = service_manager._fetch_ecs_task_ids(
        application="myapp",
        environment="dev",
        expected_count=2,
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


def test_build_cloudwatch_live_tail_url():
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())

    cloudwatch_url = service_manager._build_cloudwatch_live_tail_url(
        account_id="111222333",
        log_group="/platform/ecs/service/myapp/dev/web",
        log_streams=["stream1/test", "stream2/test"],
    )

    assert (
        cloudwatch_url
        == "https://eu-west-2.console.aws.amazon.com/cloudwatch/home?region=eu-west-2#logsV2:live-tail$3FlogGroupArns$3D~(~'arn*3aaws*3alogs*3aeu-west-2*3a111222333*3alog-group*3a*2fplatform*2fecs*2fservice*2fmyapp*2fdev*2fweb*3a*2a)$26logStreamNames$3D~(~'stream1*2ftest~'stream2*2ftest)"
    )


@patch("dbt_platform_helper.domain.service.time.sleep", return_value=None)
def test_fetch_ecs_task_ids_times_out(time_sleep):
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())
    expected_count = 3

    # One task is returned instead of the 3 tasks expected
    mocks.ecs_provider.get_ecs_task_arns.return_value = [
        "arn:aws:ecs:eu-west-2:111122223333:task/myapp-dev-cluster/task1234"
    ]

    # Fake time: 0 = deadline starts, 1 = loop once, 601 = timeout and exit
    with patch("dbt_platform_helper.domain.service.time.monotonic", side_effect=[0, 1, 601]):
        with pytest.raises(PlatformException) as e:
            service_manager._fetch_ecs_task_ids(
                application="myapp",
                environment="dev",
                deployment_id="deployment-id",
                expected_count=expected_count,
            )

    assert "Timed out waiting for 3 RUNNING ECS task(s)" in str(e.value)


@patch("dbt_platform_helper.domain.service.time.sleep", return_value=None)
def test_monitor_ecs_deployment_success(time_sleep):
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())

    mocks.logs_provider.filter_log_events.return_value = {"events": []}
    mocks.ecs_provider.get_service_rollout_state.return_value = ("SUCCESSFUL", None)

    # Fake time: 0 = deadline starts, 1 = loop once
    with patch("dbt_platform_helper.domain.service.time.monotonic", side_effect=[0, 1]):
        deployment_success = service_manager._monitor_ecs_deployment("myapp", "dev", "web")
    assert deployment_success is True


@patch("dbt_platform_helper.domain.service.time.sleep", return_value=None)
def test_monitor_ecs_deployment_failed(time_sleep):
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())

    mocks.logs_provider.filter_log_events.return_value = {"events": []}
    mocks.ecs_provider.get_service_rollout_state.return_value = (
        "ROLLBACK_SUCCESSFUL",
        "There was an error",
    )

    # Fake time: 0 = deadline starts, 1 = loop once
    with patch("dbt_platform_helper.domain.service.time.monotonic", side_effect=[0, 1]):
        with pytest.raises(PlatformException) as e:
            service_manager._monitor_ecs_deployment("myapp", "dev", "web")
    assert "ECS deployment failed: There was an error" in str(e.value)


@patch("dbt_platform_helper.domain.service.time.sleep", return_value=None)
def test_monitor_ecs_deployment_raises_exception(time_sleep):
    mocks = ServiceManagerMocks()
    service_manager = ServiceManager(**mocks.params())

    mocks.logs_provider.filter_log_events.return_value = {"events": []}
    mocks.ecs_provider.get_service_rollout_state.side_effect = Exception("An exception")

    # Fake time: 0 = deadline starts, 1 = loop once
    with patch("dbt_platform_helper.domain.service.time.monotonic", side_effect=[0, 1]):
        with pytest.raises(PlatformException) as e:
            service_manager._monitor_ecs_deployment("myapp", "dev", "web")
    assert "Failed to fetch ECS rollout state: An exception" in str(e.value)
