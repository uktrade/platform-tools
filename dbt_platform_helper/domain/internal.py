import datetime
import json
import time
from typing import Any

from dbt_platform_helper.constants import IMAGE_TAG_ENV_VAR
from dbt_platform_helper.entities.service import ServiceConfig
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigLoader
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.providers.environment_variable import (
    EnvironmentVariableProvider,
)
from dbt_platform_helper.providers.logs import LogsProvider
from dbt_platform_helper.providers.s3 import S3Provider
from dbt_platform_helper.providers.yaml_file import YamlFileProvider
from dbt_platform_helper.utils.application import load_application


class Internal:

    def __init__(
        self,
        ecs_provider: ECS,
        load_application=load_application,
        config_provider=ConfigProvider(ConfigValidator()),
        loader: ConfigLoader = ConfigLoader(),
        s3_provider: S3Provider = S3Provider(),
        logs_provider: LogsProvider = LogsProvider(),
    ):
        self.ecs_provider = ecs_provider
        self.load_application = load_application
        self.config_provider = config_provider
        self.loader = loader
        self.s3_provider = s3_provider
        self.logs_provider = logs_provider

    def deploy(
        self, service: str, environment: str, application: str, image_tag_override: str = None
    ):
        """Register a new ECS task definition revision, update the ECS service
        with it, and output Cloudwatch logs until deployment is complete."""

        service_config = YamlFileProvider.load(
            f"terraform/services/{environment}/{service}/service-config.yml"
        )

        service_model = self.loader.load_into_model(service_config, ServiceConfig)
        application_obj = self.load_application(app=application)
        application_envs = application_obj.environments
        account_id = application_envs.get(environment).account_id

        s3_response = self.s3_provider.get_object(
            bucket_name=f"ecs-container-definitions-{application}-{environment}",
            object_key=f"{application}/{environment}/{service_model.name}.json",
        )

        container_definitions = json.loads(s3_response)

        image_tag = image_tag_override or EnvironmentVariableProvider.get(IMAGE_TAG_ENV_VAR)

        task_def_arn = self.ecs_provider.register_task_definition(
            service_model=service_model,
            environment=environment,
            application=application,
            image_tag=image_tag,
            account_id=account_id,
            container_definitions=container_definitions,
        )

        print(f"Task definition successfully registered with ARN '{task_def_arn}'.\n")

        service_response = self.ecs_provider.update_service(
            service_model, task_def_arn, environment, application
        )

        print(f"Successfully updated ECS service '{service_response['serviceName']}'.\n")

        task_ids = self._fetch_ecs_task_ids(
            application=application,
            environment=environment,
            service_model=service_model,
            service_response=service_response,
        )

        print(f"Detected {len(task_ids)} new ECS task(s) with the following ID(s) {task_ids}.")

        container_names = self.ecs_provider.get_container_names_from_ecs_tasks(
            cluster_name=f"{application}-{environment}-cluster",
            task_ids=task_ids,
        )

        log_streams = self._build_log_stream_names(
            task_ids=task_ids, container_names=container_names, stream_prefix="platform"
        )

        self._monitor_ecs_deployment(
            application=application,
            environment=environment,
            service=service_model.name,
            log_streams=log_streams,
        )

    @staticmethod
    def _build_log_stream_names(
        task_ids: list[str], container_names: list[str], stream_prefix: str
    ) -> list[str]:
        """Manually build names of the log stream that will get created."""

        log_streams = []
        for id in task_ids:
            for name in container_names:
                log_streams.append(f"{stream_prefix}/{name}/{id}")

        return log_streams

    def _fetch_ecs_task_ids(
        self,
        application: str,
        environment: str,
        service_model: ServiceConfig,
        service_response: dict[str, Any],
    ) -> list[str]:
        """Return ECS task ID(s) of tasks started by the PRIMARY ECS
        deployment."""

        deployment_id = None
        for dep in service_response["deployments"]:
            if dep["status"] == "PRIMARY":
                deployment_id = dep["id"]
                break
        if not deployment_id:
            raise PlatformException(
                f"\nUnable to find primary ECS deployment for service '{service_response['serviceName']}'\n"
            )

        print(f"New ECS Deployment with ID '{deployment_id}' has been triggered.\n")

        timeout_seconds = 600
        deadline = time.monotonic() + timeout_seconds  # 10 minute deadline before timing out

        print(f"Waiting for the new ECS task(s) to spin up.\n")

        while time.monotonic() < deadline:
            task_arns = self.ecs_provider.get_ecs_task_arns(
                cluster=f"{application}-{environment}-cluster",
                started_by=deployment_id,
                desired_status="RUNNING",
            )

            if len(task_arns) >= service_model.count:
                break

            time.sleep(2)

        if len(task_arns) < service_model.count:
            raise PlatformException(
                f"Timed out waiting for {service_model.count} RUNNING ECS task(s) to spin up after {timeout_seconds}s. Got {len(task_arns)} instead."
            )

        task_ids = []
        for arn in task_arns:
            task_ids.append(arn.rsplit("/", 1)[-1])
        return task_ids

    def _monitor_ecs_deployment(
        self, application: str, environment: str, service: str, log_streams: list[str]
    ) -> bool:
        """
        Loop that prints new CloudWatch log lines for this service.

        Keeps going until rollout state is COMPLETED/FAILED or else times out.
        """

        cluster_name = f"{application}-{environment}-cluster"
        ecs_service_name = f"{application}-{environment}-{service}"
        log_group = f"/platform/ecs/service/{application}/{environment}/{service}"

        timeout_seconds = 600
        deadline = time.monotonic() + timeout_seconds  # 10 minute deadline before timing out
        start_time_ms = int(time.time() * 1000)

        print(f"\nTailing CloudWatch logs for ECS deployment to service '{ecs_service_name}' ...\n")

        self.logs_provider.check_log_streams_present(
            log_group=log_group, expected_log_streams=log_streams
        )

        while time.monotonic() < deadline:
            response = self.logs_provider.filter_log_events(
                log_group=log_group, log_streams=log_streams, start_time=start_time_ms
            )

            for event in response.get("events", []):
                timestamp = datetime.datetime.fromtimestamp(event["timestamp"] / 1000)
                print(f"[{event['logStreamName']}] [{timestamp}] {event['message'].rstrip()}")
                start_time_ms = (
                    event["timestamp"] + 1
                )  # move start_time_ms forward to avoid reprinting the same log

            try:
                state, reason = self.ecs_provider.get_service_rollout_state(
                    cluster_name=cluster_name, service_name=ecs_service_name
                )
            except Exception as e:
                raise PlatformException(f"Failed to fetch ECS rollout state: {e}")

            if state == "COMPLETED":
                print("\nECS deployment complete!")
                return True
            if state == "FAILED":
                raise PlatformException(f"\nECS deployment failed: {reason or 'unknown reason'}")

            time.sleep(2)

        raise PlatformException(
            f"Timed out after {timeout_seconds}s waiting for '{ecs_service_name}' to stabilise."
        )
