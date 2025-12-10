import json
import os
import time
import urllib.parse
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime
from datetime import timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

from dbt_platform_helper.constants import IMAGE_TAG_ENV_VAR
from dbt_platform_helper.constants import PLATFORM_HELPER_PACKAGE_NAME
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_OVERRIDE_KEY
from dbt_platform_helper.constants import SERVICE_CONFIG_FILE
from dbt_platform_helper.constants import SERVICE_DIRECTORY
from dbt_platform_helper.constants import (
    TERRAFORM_ECS_SERVICE_MODULE_SOURCE_OVERRIDE_ENV_VAR,
)
from dbt_platform_helper.constants import TERRAFORM_MODULE_SOURCE_TYPE_ENV_VAR
from dbt_platform_helper.domain.terraform_environment import (
    EnvironmentNotFoundException,
)
from dbt_platform_helper.entities.service import ServiceConfig
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.autoscaling import AutoscalingProvider
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.providers.environment_variable import (
    EnvironmentVariableProvider,
)
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.logs import LogsProvider
from dbt_platform_helper.providers.s3 import S3Provider
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider
from dbt_platform_helper.providers.version import InstalledVersionProvider
from dbt_platform_helper.providers.yaml_file import YamlFileProvider
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.deep_merge import deep_merge

SERVICE_TYPES = ["Load Balanced Web Service", "Backend Service"]
DEPLOYMENT_TIMEOUT_SECONDS = 1200
POLL_INTERVAL_SECONDS = 5

# TODO add schema version to service config


class ServiceManager:
    def __init__(
        self,
        config_provider=ConfigProvider(ConfigValidator()),
        io: ClickIOProvider = ClickIOProvider(),
        file_provider=YamlFileProvider,
        manifest_provider: TerraformManifestProvider = None,
        platform_helper_version_override: str = None,
        load_application=load_application,
        installed_version_provider: InstalledVersionProvider = InstalledVersionProvider(),
        ecs_provider: ECS = None,
        s3_provider: S3Provider = None,
        logs_provider: LogsProvider = None,
        autoscaling_provider: AutoscalingProvider = None,
    ):

        self.file_provider = file_provider
        self.config_provider = config_provider
        self.io = io
        self.manifest_provider = manifest_provider or TerraformManifestProvider()
        self.platform_helper_version_override = (
            platform_helper_version_override
            or EnvironmentVariableProvider.get(PLATFORM_HELPER_VERSION_OVERRIDE_KEY)
        )
        self.load_application = load_application
        self.installed_version_provider = installed_version_provider
        self.ecs_provider = ecs_provider
        self.s3_provider = s3_provider
        self.logs_provider = logs_provider
        self.autoscaling_provider = autoscaling_provider

    def generate(self, environment: str, services: list[str]):

        config = self.config_provider.get_enriched_config()
        application_name = config.get("application", "")
        application = self.load_application(app=application_name)

        if environment not in application.environments:
            raise EnvironmentNotFoundException(
                f"Cannot generate Terraform for environment '{environment}'. It does not exist in your configuration."
            )

        platform_helper_version_for_template: str = (
            self.platform_helper_version_override
            or config.get("default_versions", {}).get("platform-helper")
        )

        source_type = EnvironmentVariableProvider.get(TERRAFORM_MODULE_SOURCE_TYPE_ENV_VAR)

        if source_type == "LOCAL":
            module_source_override = ServiceConfig.local_terraform_source
        elif source_type == "OVERRIDE":
            module_source_override = EnvironmentVariableProvider.get(
                TERRAFORM_ECS_SERVICE_MODULE_SOURCE_OVERRIDE_ENV_VAR
            )
        else:
            module_source_override = None

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        service_models = self.get_service_models(application, environment, services)

        for service in service_models:

            model_dump = service.model_dump(
                exclude_none=True,
                by_alias=True,
                mode="json",
            )  # Use by_alias=True so that the Cooldown field 'in_' is written as 'in' in the output

            output_path = Path(
                f"terraform/{SERVICE_DIRECTORY}/{environment}/{service.name}/{SERVICE_CONFIG_FILE}"
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self.file_provider.write(
                str(output_path),
                model_dump,
                f"# WARNING: This is an autogenerated file, not for manual editing.\n# Generated by platform-helper {version('dbt-platform-helper')} / {timestamp}.\n",
            )

            self.manifest_provider.generate_service_config(
                service,
                environment,
                platform_helper_version_for_template,
                config,
                module_source_override,
            )

    def get_service_models(self, application, environment, services=None) -> list[ServiceConfig]:
        if not services:
            services = []
            try:
                for dir in Path("services").iterdir():
                    if dir.is_dir():
                        config_path = dir / SERVICE_CONFIG_FILE
                        if config_path.exists():
                            services.append(dir.name)
                        else:
                            self.io.warn(
                                f"Failed loading service name from {dir.name}.\n"
                                "Please ensure that your '/services' directory follows the correct structure (i.e. /services/<service_name>/service-config.yml) and the 'service-config.yml' contents are correct."
                            )
            except Exception as e:
                self.io.abort_with_error(f"Failed extracting services with exception, {e}")

        service_models = []
        for service in services:
            file_content = self.file_provider.load(
                f"{SERVICE_DIRECTORY}/{service}/{SERVICE_CONFIG_FILE}"
            )

            file_content = self.file_provider.find_and_replace(
                config=file_content,
                strings=[
                    "${PLATFORM_APPLICATION_NAME}",
                    "${PLATFORM_ENVIRONMENT_NAME}",
                ],
                replacements=[application.name, environment],
            )

            env_overrides = file_content.get("environments", {}).get(environment)
            if env_overrides:
                merged_config = deep_merge(file_content, env_overrides)
            else:
                merged_config = file_content
            merged_config.pop("environments", None)

            service_model = ServiceConfig(**merged_config)
            service_models.append(service_model)

        return service_models

    def migrate_copilot_manifests(self) -> None:
        service_directory = Path("services/")
        service_directory.mkdir(parents=True, exist_ok=True)

        for dirname, _, filenames in os.walk("copilot"):
            if "manifest.yml" in filenames and "environments" not in dirname:
                copilot_manifest = self.file_provider.load(f"{dirname}/manifest.yml")
                service_manifest = OrderedDict(deepcopy(copilot_manifest))

                if service_manifest["type"] not in SERVICE_TYPES:
                    continue

                if "environments" in service_manifest:
                    for env in service_manifest["environments"]:
                        env_config = service_manifest["environments"][env]
                        if "http" in env_config:
                            if "alb" in env_config["http"]:
                                del env_config["http"]["alb"]
                            if isinstance(env_config["http"].get("alias", []), str):
                                env_config["http"]["alias"] = [env_config["http"]["alias"]]
                            if "healthcheck" in env_config["http"]:
                                if "interval" in env_config["http"]["healthcheck"]:
                                    interval = env_config["http"]["healthcheck"]["interval"]
                                    env_config["http"]["healthcheck"]["interval"] = int(
                                        interval.rstrip("s")
                                    )
                                if "timeout" in env_config["http"]["healthcheck"]:
                                    timeout = env_config["http"]["healthcheck"]["timeout"]
                                    env_config["http"]["healthcheck"]["timeout"] = int(
                                        timeout.rstrip("s")
                                    )
                                if "grace_period" in env_config["http"]["healthcheck"]:
                                    grace_period = env_config["http"]["healthcheck"]["grace_period"]
                                    env_config["http"]["healthcheck"]["grace_period"] = int(
                                        grace_period.rstrip("s")
                                    )
                        if "image" in env_config:
                            if "healthcheck" in env_config["image"]:
                                if "interval" in env_config["image"]["healthcheck"]:
                                    interval = env_config["image"]["healthcheck"]["interval"]
                                    env_config["image"]["healthcheck"]["interval"] = int(
                                        interval.rstrip("s")
                                    )
                                if "timeout" in env_config["image"]["healthcheck"]:
                                    timeout = env_config["image"]["healthcheck"]["timeout"]
                                    env_config["image"]["healthcheck"]["timeout"] = int(
                                        timeout.rstrip("s")
                                    )
                                if "start_period" in env_config["image"]["healthcheck"]:
                                    start_period = env_config["image"]["healthcheck"][
                                        "start_period"
                                    ]
                                    env_config["image"]["healthcheck"]["start_period"] = int(
                                        start_period.rstrip("s")
                                    )
                        if "count" in env_config:
                            if "cooldown" in env_config["count"]:
                                if "in" in env_config["count"]["cooldown"]:
                                    scaling_in = env_config["count"]["cooldown"]["in"]
                                    env_config["count"]["cooldown"]["in"] = int(
                                        scaling_in.rstrip("s")
                                    )
                                if "out" in env_config["count"]["cooldown"]:
                                    scaling_out = env_config["count"]["cooldown"]["out"]
                                    env_config["count"]["cooldown"]["out"] = int(
                                        scaling_out.rstrip("s")
                                    )
                        if "network" in env_config:
                            del env_config["network"]
                        if "observability" in env_config:
                            del env_config["observability"]

                if "healthcheck" in service_manifest.get("http", {}):
                    if "interval" in service_manifest["http"]["healthcheck"]:
                        interval = service_manifest["http"]["healthcheck"]["interval"]
                        service_manifest["http"]["healthcheck"]["interval"] = int(
                            interval.rstrip("s")
                        )
                    if "timeout" in service_manifest["http"]["healthcheck"]:
                        timeout = service_manifest["http"]["healthcheck"]["timeout"]
                        service_manifest["http"]["healthcheck"]["timeout"] = int(
                            timeout.rstrip("s")
                        )
                    if "grace_period" in service_manifest["http"]["healthcheck"]:
                        grace_period = service_manifest["http"]["healthcheck"]["grace_period"]
                        service_manifest["http"]["healthcheck"]["grace_period"] = int(
                            grace_period.rstrip("s")
                        )

                if "image" in service_manifest:
                    if "healthcheck" in service_manifest["image"]:
                        if "interval" in service_manifest["image"]["healthcheck"]:
                            interval = service_manifest["image"]["healthcheck"]["interval"]
                            service_manifest["image"]["healthcheck"]["interval"] = int(
                                interval.rstrip("s")
                            )
                        if "timeout" in service_manifest["image"]["healthcheck"]:
                            timeout = service_manifest["image"]["healthcheck"]["timeout"]
                            service_manifest["image"]["healthcheck"]["timeout"] = int(
                                timeout.rstrip("s")
                            )
                        if "start_period" in service_manifest["image"]["healthcheck"]:
                            start_period = service_manifest["image"]["healthcheck"]["start_period"]
                            service_manifest["image"]["healthcheck"]["start_period"] = int(
                                start_period.rstrip("s")
                            )

                if "cooldown" in env_config.get("count", {}):
                    if "in" in env_config["count"]["cooldown"]:
                        scaling_in = env_config["count"]["cooldown"]["in"]
                        env_config["count"]["cooldown"]["in"] = int(scaling_in.rstrip("s"))
                    if "out" in env_config["count"]["cooldown"]:
                        scaling_out = env_config["count"]["cooldown"]["out"]
                        env_config["count"]["cooldown"]["out"] = int(scaling_out.rstrip("s"))

                if "network" in service_manifest:
                    del service_manifest["network"]
                if "observability" in service_manifest:
                    del service_manifest["observability"]

                if "entrypoint" in service_manifest:
                    if isinstance(service_manifest["entrypoint"], str):
                        service_manifest["entrypoint"] = [service_manifest["entrypoint"]]

                if "alias" in service_manifest.get("http", {}):
                    if isinstance(service_manifest["http"]["alias"], str):
                        service_manifest["http"]["alias"] = [service_manifest["http"]["alias"]]

                service_manifest = self.file_provider.find_and_replace(
                    config=service_manifest,
                    strings=["${COPILOT_APPLICATION_NAME}", "${COPILOT_ENVIRONMENT_NAME}"],
                    replacements=["${PLATFORM_APPLICATION_NAME}", "${PLATFORM_ENVIRONMENT_NAME}"],
                )

                service_manifest = self.file_provider.remove_empty_keys(service_manifest)

                if "sidecars" in service_manifest:
                    new_sidecars = {}
                    writable_directories = []

                    for sidecar_name, sidecar in service_manifest["sidecars"].items():
                        if "chown" not in sidecar.get("command", "") and "chmod" not in sidecar.get(
                            "command", ""
                        ):
                            new_sidecars[sidecar_name] = sidecar
                        if "chown" in sidecar.get("command", "") and "mount_points" in sidecar:
                            for mountpoint in sidecar["mount_points"]:
                                writable_directories.append(mountpoint["path"])

                    service_manifest["sidecars"] = new_sidecars
                    if "storage" in service_manifest:
                        service_manifest["storage"]["writable_directories"] = writable_directories

                service_path = service_directory / service_manifest["name"]

                self.io.info(
                    FileProvider.mkfile(
                        service_path,
                        "service-config.yml",
                        "",
                        overwrite=True,
                    )
                )

                current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = f"# Generated by platform-helper {self.installed_version_provider.get_semantic_version(PLATFORM_HELPER_PACKAGE_NAME)} / {current_date}.\n\n"

                self.file_provider.write(
                    f"{service_path}/service-config.yml", dict(service_manifest), message
                )

    def deploy(
        self,
        service: str,
        environment: str,
        application: str,
        image_tag: str = None,
    ):
        """Register a new ECS task definition revision, update the ECS service
        with it, monitor service, task and container logs, and wait until
        deployment is complete."""

        start_time = datetime.now(timezone.utc)
        cluster_name = f"{application}-{environment}-cluster"
        ecs_service_name = f"{application}-{environment}-{service}"

        s3_response = self.s3_provider.get_object(
            bucket_name=f"ecs-task-definitions-{application}-{environment}",
            object_key=f"{application}/{environment}/{service}.json",
        )

        task_definition = json.loads(s3_response)

        image_tag = image_tag or EnvironmentVariableProvider.get(IMAGE_TAG_ENV_VAR)

        self.io.info(
            f"Deploying image tag '{image_tag}' to service '{ecs_service_name}' in environment '{environment}'.\n"
        )

        task_def_arn = self.ecs_provider.register_task_definition(
            service=service,
            image_tag=image_tag,
            task_definition=task_definition,
        )

        self._output_with_timestamp(
            f"Task definition successfully registered with ARN '{task_def_arn}'."
        )

        autoscaling_response = self.autoscaling_provider.describe_autoscaling_target(
            cluster_name=cluster_name, ecs_service_name=ecs_service_name
        )
        desired_count = autoscaling_response.get("MinCapacity", 1)

        update_response = self.ecs_provider.update_service(
            service=service,
            task_def_arn=task_def_arn,
            environment=environment,
            application=application,
            desired_count=desired_count,
        )

        self._output_with_timestamp(
            f"Successfully updated ECS service '{update_response['serviceName']}'."
        )

        primary_deployment_id = self._get_primary_deployment_id(service_response=update_response)

        self._output_with_timestamp(
            f"New deployment with ID '{primary_deployment_id}' has been triggered."
        )

        seen_events = set()
        deadline = time.monotonic() + DEPLOYMENT_TIMEOUT_SECONDS

        while time.monotonic() < deadline:
            service_response = self.ecs_provider.describe_service(
                application=application, environment=environment, service=service
            )
            primary_deployment_id = self._get_primary_deployment_id(
                service_response=service_response
            )

            self._monitor_service_events(
                service_response=service_response, seen_events=seen_events, start_time=start_time
            )

            task_ids = self._wait_for_new_tasks(
                cluster_name=cluster_name, deployment_id=primary_deployment_id
            )
            task_response = self.ecs_provider.describe_tasks(
                cluster_name=f"{application}-{environment}-cluster",
                task_ids=task_ids,
            )

            log_group = f"/platform/ecs/service/{application}/{environment}/{service}"
            self._monitor_task_events(
                task_response=task_response, seen_events=seen_events, log_group=log_group
            )

            state, reason = self.ecs_provider.get_service_deployment_state(
                cluster_name=cluster_name,
                service_name=ecs_service_name,
                start_time=start_time.timestamp(),
            )

            if state == "SUCCESSFUL":
                self._output_with_timestamp("Deployment complete.")
                return
            if state in ["STOPPED", "ROLLBACK_SUCCESSFUL", "ROLLBACK_FAILED"]:
                raise PlatformException(f"Deployment failed: {reason or 'unknown reason'}")

            time.sleep(POLL_INTERVAL_SECONDS)

        raise PlatformException("Timed out waiting for service to stabilise.")

    @staticmethod
    def _get_primary_deployment_id(service_response: dict[str, Any]):
        for dep in service_response["deployments"]:
            if dep["status"] == "PRIMARY":
                return dep["id"]
        raise PlatformException(
            f"Unable to find primary ECS deployment for service '{service_response['serviceName']}'."
        )

    def _monitor_service_events(
        self, service_response: dict[str, Any], seen_events: set[str], start_time: datetime
    ):
        """Output ECS service events during deployment."""

        for event in reversed(service_response.get("events", [])):
            if event["id"] not in seen_events and event["createdAt"] > start_time:
                seen_events.add(event["id"])
                timestamp = event["createdAt"].strftime("%H:%M:%S")
                message = event["message"]
                self._output_with_timestamp(
                    message=message,
                    error=("error" in message or "failed" in message),
                    timestamp=timestamp,
                )

    def _monitor_task_events(
        self, task_response: list[dict[str, Any]], seen_events: set[str], log_group: str
    ):
        """Output ECS task and container errors during deployment."""

        for task in task_response:
            for container in task["containers"]:
                if container.get("exitCode", 0) != 1:
                    continue

                task_id = task["taskArn"].split("/")[-1]
                container_name = container["name"]
                log_stream = f"platform/{container_name}/{task_id}"

                if f"{task_id}-{container_name}" not in seen_events:
                    seen_events.add(f"{task_id}-{container_name}")
                    self._output_with_timestamp(
                        message=f"Container '{container_name}' stopped in task '{task_id}'.",
                        error=True,
                    )
                    log_url = f"https://eu-west-2.console.aws.amazon.com/cloudwatch/home?region=eu-west-2#logsV2:log-groups/log-group/{urllib.parse.quote_plus(log_group)}/log-events/{urllib.parse.quote_plus(log_stream)}"
                    self._output_with_timestamp(
                        message=f"View CloudWatch log: {log_url}", error=True
                    )

                log_events = self.logs_provider.get_log_stream_events(
                    log_group=log_group,
                    log_stream=log_stream,
                    limit=20,
                )

                for event in log_events:
                    try:
                        message = json.loads(event["message"])
                    except json.decoder.JSONDecodeError:
                        message = event["message"]

                    if f"{task_id}-{message}" not in seen_events:
                        seen_events.add(f"{task_id}-{message}")
                        self._output_with_timestamp(message=message, error=True)

    def _wait_for_new_tasks(self, cluster_name: str, deployment_id: str) -> list[str]:
        """Return first ECS task ID started by the PRIMARY ECS deployment."""

        timeout_seconds = 180
        deadline = time.monotonic() + timeout_seconds

        while time.monotonic() < deadline:
            task_arns = self.ecs_provider.get_ecs_task_arns(
                cluster=cluster_name,
                started_by=deployment_id,
                desired_status="RUNNING",
            )

            if task_arns:
                break

            time.sleep(POLL_INTERVAL_SECONDS)

        if not task_arns:
            raise PlatformException(
                f"Timed out waiting for RUNNING ECS tasks to spin up after {timeout_seconds}s."
            )

        task_ids = []
        for arn in task_arns:
            task_ids.append(arn.rsplit("/", 1)[-1])
        return task_ids

    def _output_with_timestamp(self, message: str, error: bool = False, timestamp: datetime = None):
        if not timestamp:
            timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")

        if error:
            self.io.deploy_error(f"[{timestamp}] {message}")
        else:
            self.io.info(f"[{timestamp}] {message}")
