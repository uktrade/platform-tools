from datetime import datetime
from importlib.metadata import version
from pathlib import Path

from dbt_platform_helper.constants import IMAGE_TAG_DEFAULT
from dbt_platform_helper.constants import IMAGE_TAG_ENV_VAR
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
from dbt_platform_helper.providers.config import ConfigLoader
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.environment_variable import (
    EnvironmentVariableProvider,
)
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider
from dbt_platform_helper.providers.yaml_file import YamlFileProvider
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.deep_merge import deep_merge

# TODO add schema version too service config


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

    def generate(self, environments: list[str], services: list[str], flag_image_tag: str = None):

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

        image_tag = flag_image_tag or self.environment_variable_provider.get(
            IMAGE_TAG_ENV_VAR, IMAGE_TAG_DEFAULT
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
