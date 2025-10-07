import json
import os
import time
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime
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
DEPLOYMENT_TIMEOUT_SECONDS = 600
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

    def generate(self, environment: str, services: list[str]):

        config = self.config_provider.get_enriched_config()
        application_name = config.get("application", "")
        application = self.load_application(app=application_name)

        if environment not in application.environments:
            raise EnvironmentNotFoundException(
                f"Cannot generate Terraform for environment '{environment}'. It does not exist in your configuration."
            )

        if not services:
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

            file_content = YamlFileProvider.find_and_replace(
                config=file_content,
                strings=[
                    "${PLATFORM_APPLICATION_NAME}",
                    "${PLATFORM_ENVIRONMENT_NAME}",
                ],
                replacements=[application.name, environment],
            )
            service_models.append(ServiceConfig(**file_content))

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

        for service in service_models:

            model_dump = service.model_dump(exclude_none=True)
            env_overrides = model_dump.get("environments", {}).get(environment)
            if env_overrides:
                merged_config = deep_merge(model_dump, env_overrides)
            else:
                merged_config = model_dump.copy()
            merged_config.pop("environments", None)

            output_path = Path(
                f"terraform/{SERVICE_DIRECTORY}/{environment}/{service.name}/{SERVICE_CONFIG_FILE}"
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self.file_provider.write(
                str(output_path),
                merged_config,
                f"# WARNING: This is an autogenerated file, not for manual editing.\n# Generated by platform-helper {version('dbt-platform-helper')} / {timestamp}.\n",
            )

            self.manifest_provider.generate_service_config(
                service,
                environment,
                platform_helper_version_for_template,
                config,
                module_source_override,
            )

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
                        if "count" in env_config:
                            if (
                                isinstance(env_config["count"], dict)
                                and "range" in env_config["count"]
                            ):
                                count_range = str(env_config["count"]["range"]).split("-")
                                env_config["count"]["range"] = {
                                    "min": int(count_range[0]),
                                    "max": int(count_range[1]),
                                }

                if "entrypoint" in service_manifest:
                    if isinstance(service_manifest["entrypoint"], str):
                        service_manifest["entrypoint"] = [service_manifest["entrypoint"]]

                if "count" in service_manifest:
                    if (
                        isinstance(service_manifest["count"], dict)
                        and "range" in service_manifest["count"]
                    ):
                        count_range = str(service_manifest["count"]["range"]).split("-")
                        service_manifest["count"]["range"] = {
                            "min": int(count_range[0]),
                            "max": int(count_range[1]),
                        }

                service_manifest = self.file_provider.find_and_replace(
                    config=service_manifest,
                    strings=["${COPILOT_APPLICATION_NAME}", "${COPILOT_ENVIRONMENT_NAME}"],
                    replacements=["${PLATFORM_APPLICATION_NAME}", "${PLATFORM_ENVIRONMENT_NAME}"],
                )

                service_manifest = self.file_provider.remove_empty_keys(service_manifest)

                if "sidecars" in service_manifest:
                    new_sidecars = {}

                    for sidecar_name, sidecar in service_manifest["sidecars"].items():
                        if "command" in sidecar and (
                            "chown" in sidecar["command"] or "chmod" in sidecar["command"]
                        ):
                            continue
                        new_sidecars[sidecar_name] = sidecar

                    service_manifest["sidecars"] = new_sidecars

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

    def deploy(self, service: str, environment: str, application: str, image_tag: str = None):
        """Register a new ECS task definition revision, update the ECS service
        with it, and output Cloudwatch logs until deployment is complete."""

        application_obj = self.load_application(app=application)
        application_envs = application_obj.environments
        account_id = application_envs.get(environment).account_id

        s3_response = self.s3_provider.get_object(
            bucket_name=f"ecs-task-definitions-{application}-{environment}",
            object_key=f"{application}/{environment}/{service}.json",
        )

        task_definition = json.loads(s3_response)

        image_tag = image_tag or EnvironmentVariableProvider.get(IMAGE_TAG_ENV_VAR)

        task_def_arn = self.ecs_provider.register_task_definition(
            service=service,
            image_tag=image_tag,
            task_definition=task_definition,
        )

        self.io.info(f"Task definition successfully registered with ARN '{task_def_arn}'.\n")

        service_response = self.ecs_provider.update_service(
            service=service,
            task_def_arn=task_def_arn,
            environment=environment,
            application=application,
        )

        self.io.info(f"Successfully updated ECS service '{service_response['serviceName']}'.\n")

        primary_deployment_id = self._get_primary_deployment_id(service_response=service_response)
        self.io.info(f"New ECS Deployment with ID '{primary_deployment_id}' has been triggered.\n")

        expected_count = service_response.get("desiredCount", 1)
        task_ids = self._fetch_ecs_task_ids(
            application=application,
            environment=environment,
            deployment_id=primary_deployment_id,
            expected_count=expected_count,
        )

        self.io.info(
            f"Detected {len(task_ids)} new ECS task(s) with the following ID(s) {task_ids}.\n"
        )

        container_names = self.ecs_provider.get_container_names_from_ecs_tasks(
            cluster_name=f"{application}-{environment}-cluster",
            task_ids=task_ids,
        )

        log_streams = self._build_log_stream_names(
            task_ids=task_ids, container_names=container_names, stream_prefix="platform"
        )

        log_group = f"/platform/ecs/service/{application}/{environment}/{service}"
        self.logs_provider.check_log_streams_present(
            log_group=log_group, expected_log_streams=log_streams
        )

        cloudwatch_url = self._build_cloudwatch_live_tail_url(
            account_id=account_id, log_group=log_group, log_streams=log_streams
        )
        self.io.info(f"View real-time deployment logs in the AWS Console: \n{cloudwatch_url}\n")

        self._monitor_ecs_deployment(
            application=application,
            environment=environment,
            service=service,
        )

    @staticmethod
    def _build_cloudwatch_live_tail_url(
        account_id: str, log_group: str, log_streams: list[str]
    ) -> str:
        """Build CloudWatch live tail URL with log group and log streams pre-
        populated in Rison format."""

        log_group_rison = log_group.replace("/", "*2f")

        delimiter = "~'"
        log_streams_rison = ""
        for stream in log_streams:
            stream_rison = stream.replace("/", "*2f")
            log_streams_rison = log_streams_rison + f"{delimiter}{stream_rison}"

        base = "https://eu-west-2.console.aws.amazon.com/cloudwatch/home?region=eu-west-2#logsV2:live-tail"
        log_group_fragment = f"$3FlogGroupArns$3D~(~'arn*3aaws*3alogs*3aeu-west-2*3a{account_id}*3alog-group*3a{log_group_rison}*3a*2a)"
        log_streams_fragment = f"$26logStreamNames$3D~({log_streams_rison})"

        return base + log_group_fragment + log_streams_fragment

    @staticmethod
    def _build_log_stream_names(
        task_ids: list[str], container_names: list[str], stream_prefix: str
    ) -> list[str]:
        """Manually build names of the log stream that will get created."""

        log_streams = []
        for id in task_ids:
            for name in container_names:
                if not name.startswith(
                    "ecs-service-connect"
                ):  # ECS Service Connect container logs are noisy and not relevant in most cases
                    log_streams.append(f"{stream_prefix}/{name}/{id}")

        return log_streams

    @staticmethod
    def _get_primary_deployment_id(service_response: dict[str, Any]):
        for dep in service_response["deployments"]:
            if dep["status"] == "PRIMARY":
                return dep["id"]
        raise PlatformException(
            f"\nUnable to find primary ECS deployment for service '{service_response['serviceName']}'\n"
        )

    def _fetch_ecs_task_ids(
        self, application: str, environment: str, deployment_id: str, expected_count: int
    ) -> list[str]:
        """Return ECS task ID(s) of tasks started by the PRIMARY ECS
        deployment."""

        timeout_seconds = DEPLOYMENT_TIMEOUT_SECONDS
        deadline = time.monotonic() + timeout_seconds  # 10 minute deadline before timing out

        self.io.info(f"Waiting for the new ECS task(s) to spin up.\n")

        while time.monotonic() < deadline:
            task_arns = self.ecs_provider.get_ecs_task_arns(
                cluster=f"{application}-{environment}-cluster",
                started_by=deployment_id,
                desired_status="RUNNING",
            )

            if len(task_arns) >= expected_count:
                break

            time.sleep(POLL_INTERVAL_SECONDS)

        if len(task_arns) < expected_count:
            raise PlatformException(
                f"Timed out waiting for {expected_count} RUNNING ECS task(s) to spin up after {timeout_seconds}s. Got {len(task_arns)} instead."
            )

        task_ids = []
        for arn in task_arns:
            task_ids.append(arn.rsplit("/", 1)[-1])
        return task_ids

    def _monitor_ecs_deployment(self, application: str, environment: str, service: str) -> bool:
        """Loop until ECS rollout state is COMPLETED/FAILED or else times
        out."""

        cluster_name = f"{application}-{environment}-cluster"
        ecs_service_name = f"{application}-{environment}-{service}"
        start_time = time.time()
        timeout_seconds = DEPLOYMENT_TIMEOUT_SECONDS
        deadline = time.monotonic() + timeout_seconds  # 10 minute deadline before timing out

        while time.monotonic() < deadline:
            try:
                state, reason = self.ecs_provider.get_service_rollout_state(
                    cluster_name=cluster_name, service_name=ecs_service_name
                )
            except Exception as e:
                raise PlatformException(f"Failed to fetch ECS rollout state: {e}")

            if state == "COMPLETED":
                self.io.info("\nECS deployment complete!")
                return True
            if state == "FAILED":
                raise PlatformException(f"\nECS deployment failed: {reason or 'unknown reason'}")

            elapsed_time = int(time.time() - start_time)
            self.io.info(f"Deployment in progress {elapsed_time}s")
            time.sleep(POLL_INTERVAL_SECONDS)

        raise PlatformException(
            f"Timed out after {timeout_seconds}s waiting for '{ecs_service_name}' to stabilise."
        )
