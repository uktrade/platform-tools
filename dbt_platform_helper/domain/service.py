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
from dbt_platform_helper.providers.config import ConfigLoader
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


# TODO add schema version to service config


class ServiceManager:
    def __init__(
        self,
        config_provider=ConfigProvider(ConfigValidator()),
        loader: ConfigLoader = ConfigLoader(),
        io: ClickIOProvider = ClickIOProvider(),
        file_provider=YamlFileProvider,
        environment_variable_provider: EnvironmentVariableProvider = None,
        manifest_provider: TerraformManifestProvider = None,
        platform_helper_version_override: str = None,
        load_application=load_application,
        installed_version_provider: InstalledVersionProvider = InstalledVersionProvider(),
        ecs_provider: ECS = None,
        s3_provider: S3Provider = S3Provider(),
        logs_provider: LogsProvider = LogsProvider(),
    ):

        self.file_provider = file_provider
        self.config_provider = config_provider
        self.loader = loader
        self.io = io
        self.environment_variable_provider = (
            environment_variable_provider or EnvironmentVariableProvider()
        )
        self.manifest_provider = manifest_provider or TerraformManifestProvider()
        self.platform_helper_version_override = (
            platform_helper_version_override
            or self.environment_variable_provider.get(PLATFORM_HELPER_VERSION_OVERRIDE_KEY)
        )
        self.load_application = load_application
        self.installed_version_provider = installed_version_provider
        self.ecs_provider = ecs_provider
        self.s3_provider = s3_provider
        self.logs_provider = logs_provider

    def generate(self, environment: str, services: list[str], image_tag_flag: str = None):

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

        image_tag = image_tag_flag or self.environment_variable_provider.get(IMAGE_TAG_ENV_VAR)
        if not image_tag:
            raise PlatformException(
                f"An image tag must be provided to deploy a service. This can be set by the $IMAGE_TAG environment variable, or the --image-tag flag."
            )

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
                    "${IMAGE_TAG}",
                ],
                replacements=[application.name, environment, image_tag],
            )
            service_models.append(
                self.loader.load_into_model(
                    input=file_content,
                    model=ServiceConfig,
                )
            )

        platform_helper_version_for_template: str = (
            self.platform_helper_version_override
            or config.get("default_versions", {}).get("platform-helper")
        )

        source_type = self.environment_variable_provider.get(TERRAFORM_MODULE_SOURCE_TYPE_ENV_VAR)

        if source_type == "LOCAL":
            module_source_override = ServiceConfig.local_terraform_source
        elif source_type == "OVERRIDE":
            module_source_override = self.environment_variable_provider.get(
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

                if "entrypoint" in service_manifest:
                    if isinstance(service_manifest["entrypoint"], str):
                        service_manifest["entrypoint"] = [service_manifest["entrypoint"]]

                service_manifest = self.file_provider.find_and_replace(
                    config=service_manifest,
                    strings=["${COPILOT_APPLICATION_NAME}", "${COPILOT_ENVIRONMENT_NAME}"],
                    replacements=["${PLATFORM_APPLICATION_NAME}", "${PLATFORM_ENVIRONMENT_NAME}"],
                )

                service_manifest = self.file_provider.remove_empty_keys(service_manifest)

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
                timestamp = datetime.fromtimestamp(event["timestamp"] / 1000)
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
