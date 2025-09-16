import os
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

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
from dbt_platform_helper.providers.environment_variable import (
    EnvironmentVariableProvider,
)
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.io import ClickIOProvider
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

    def generate(self, environments: list[str], services: list[str], image_tag_flag: str = None):

        config = self.config_provider.get_enriched_config()
        application_name = config.get("application", "")
        application = self.load_application(app=application_name)

        if not environments:
            for environment in application.environments:
                environments.append(environment)
        else:
            for environment in environments:
                if environment not in application.environments:
                    raise EnvironmentNotFoundException(
                        f"cannot generate terraform for environment {environment}.  It does not exist in your configuration"
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
            service_models.append(
                self.loader.load_into_model(
                    f"{SERVICE_DIRECTORY}/{service}/{SERVICE_CONFIG_FILE}",
                    ServiceConfig,
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

        image_tag = image_tag_flag or self.environment_variable_provider.get(IMAGE_TAG_ENV_VAR)
        if not image_tag:
            raise PlatformException(
                f"An image tag must be provided to deploy a service. This can be set by the $IMAGE_TAG environment variable, or the --image-tag flag."
            )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for service in service_models:

            for environment in environments:

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
                    image_tag,
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

                service_manifest = self.file_provider.find_and_replace(
                    service_manifest,
                    "${COPILOT_APPLICATION_NAME}",
                    "${PLATFORM_APPLICATION_NAME}",
                )

                service_manifest = self.file_provider.find_and_replace(
                    service_manifest,
                    "${COPILOT_ENVIRONMENT_NAME}",
                    "${PLATFORM_ENVIRONMENT_NAME}",
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
