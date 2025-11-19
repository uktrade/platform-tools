from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_OVERRIDE_KEY
from dbt_platform_helper.constants import (
    TERRAFORM_CODEBASE_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR,
)
from dbt_platform_helper.constants import (
    TERRAFORM_ENVIRONMENT_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR,
)
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.environment_variable import (
    EnvironmentVariableProvider,
)

ENVIRONMENT_PIPELINE_MODULE_PATH = (
    "git::git@github.com:uktrade/platform-tools.git//terraform/environment-pipelines?depth=1&ref="
)

CODEBASE_PIPELINE_MODULE_PATH = (
    "git::git@github.com:uktrade/platform-tools.git//terraform/codebase-pipelines?depth=1&ref="
)


class PipelineVersioning:
    def __init__(
        self,
        config_provider: ConfigProvider,
        environment_variable_provider: EnvironmentVariableProvider = EnvironmentVariableProvider(),
        platform_helper_version_override: str = None,
    ):
        self.config_provider = config_provider
        self.environment_variable_provider = environment_variable_provider
        self.platform_helper_version_override = platform_helper_version_override

    def get_default_version(self):
        return (
            self.config_provider.load_and_validate_platform_config()
            .get("default_versions", {})
            .get("platform-helper")
        )

    def get_template_version(self):
        if self.platform_helper_version_override:
            return self.platform_helper_version_override
        return self.get_default_version()

    def get_environment_pipeline_modules_version(self):

        environment_pipeline_module_override = self.environment_variable_provider.get(
            TERRAFORM_ENVIRONMENT_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR
        )

        if environment_pipeline_module_override:
            return environment_pipeline_module_override

        if self.platform_helper_version_override:
            return f"{ENVIRONMENT_PIPELINE_MODULE_PATH}{self.platform_helper_version_override}"

        platform_helper_env_override = self.environment_variable_provider.get(
            PLATFORM_HELPER_VERSION_OVERRIDE_KEY
        )

        if platform_helper_env_override:
            return f"{ENVIRONMENT_PIPELINE_MODULE_PATH}{platform_helper_env_override}"

        return f"{ENVIRONMENT_PIPELINE_MODULE_PATH}{self.get_default_version()}"

    def get_codebase_pipeline_modules_version(self):

        codebase_pipeline_module_override = self.environment_variable_provider.get(
            TERRAFORM_CODEBASE_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR
        )

        if codebase_pipeline_module_override:
            return codebase_pipeline_module_override

        if self.platform_helper_version_override:
            return f"{CODEBASE_PIPELINE_MODULE_PATH}{self.platform_helper_version_override}"

        platform_helper_env_override = self.environment_variable_provider.get(
            PLATFORM_HELPER_VERSION_OVERRIDE_KEY
        )

        if platform_helper_env_override:
            return f"{CODEBASE_PIPELINE_MODULE_PATH}{platform_helper_env_override}"

        return f"{CODEBASE_PIPELINE_MODULE_PATH}{self.get_default_version()}"
