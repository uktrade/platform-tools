from typing import Callable

import boto3

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.aws.opensearch import Opensearch
from dbt_platform_helper.providers.aws.redis import Redis
from dbt_platform_helper.providers.cache import Cache
from dbt_platform_helper.providers.cache import GetAWSVersionStrategy
from dbt_platform_helper.providers.io import ClickIOProvider


class ConfigValidatorError(PlatformException):
    pass


class ConfigValidator:

    def __init__(
        self,
        validations: Callable[[dict], None] = None,
        io: ClickIOProvider = ClickIOProvider(),
        session: boto3.Session = None,
    ):
        self.validations = validations or [
            self.validate_supported_redis_versions,
            self.validate_supported_opensearch_versions,
            self.validate_environment_pipelines,
            self.validate_environment_pipelines_triggers,
            self.validate_database_copy_section,
            self.validate_database_migration_input_sources,
        ]
        self.io = io
        self.session = session

    def run_validations(self, config: dict):
        for validation in self.validations:
            validation(config)

    def _validate_extension_supported_versions(
        self, config, aws_provider, extension_type, version_key
    ):
        extensions = config.get("extensions", {})
        if not extensions:
            return

        extensions_for_type = [
            extension
            for extension in config.get("extensions", {}).values()
            if extension.get("type") == extension_type
        ]

        # In this format so it can be monkey patched initially via mock_get_data fixture
        cache_provider = Cache()
        get_data_strategy = GetAWSVersionStrategy(aws_provider)
        supported_extension_versions = cache_provider.get_data(get_data_strategy)
        extensions_with_invalid_version = []

        for extension in extensions_for_type:

            environments = extension.get("environments", {})

            if not isinstance(environments, dict):
                self.io.error(
                    f"{extension_type} extension definition is invalid type, expected dictionary",
                )
                continue
            for environment, env_config in environments.items():

                # An extension version doesn't need to be specified for all environments, provided one is specified under "*".
                # So check if the version is set before checking if it's supported
                extension_version = env_config.get(version_key)
                if extension_version and extension_version not in supported_extension_versions:
                    extensions_with_invalid_version.append(
                        {"environment": environment, "version": extension_version}
                    )

        for version_failure in extensions_with_invalid_version:
            self.io.error(
                f"{extension_type} version for environment {version_failure['environment']} is not in the list of supported {extension_type} versions: {supported_extension_versions}. Provided Version: {version_failure['version']}",
            )

    def _get_client(self, service_name: str):
        if self.session:
            return self.session.client(service_name)
        return boto3.client(service_name)

    def validate_supported_redis_versions(self, config):
        return self._validate_extension_supported_versions(
            config=config,
            aws_provider=Redis(self._get_client("elasticache")),
            extension_type="redis",  # TODO: DBTP-1888: this is information which can live in the RedisProvider
            version_key="engine",  # TODO: DBTP-1888: this is information which can live in the RedisProvider
        )

    def validate_supported_opensearch_versions(self, config):
        return self._validate_extension_supported_versions(
            config=config,
            aws_provider=Opensearch(self._get_client("opensearch")),
            extension_type="opensearch",  # TODO: DBTP-1888: this is information which can live in the OpensearchProvider
            version_key="engine",  # TODO: DBTP-1888: this is information which can live in the OpensearchProvider
        )

    def validate_environment_pipelines(self, config):
        bad_pipelines = {}
        for pipeline_name, pipeline in config.get("environment_pipelines", {}).items():
            bad_envs = []
            pipeline_account = pipeline.get("account", None)
            if pipeline_account:
                for env in pipeline.get("environments", {}).keys():
                    env_account = (
                        config.get("environments", {})
                        .get(env, {})
                        .get("accounts", {})
                        .get("deploy", {})
                        .get("name")
                    )
                    if not env_account == pipeline_account:
                        bad_envs.append(env)
            if bad_envs:
                bad_pipelines[pipeline_name] = {"account": pipeline_account, "bad_envs": bad_envs}
        if bad_pipelines:
            message = "The following pipelines are misconfigured:"
            for pipeline, detail in bad_pipelines.items():
                envs = detail["bad_envs"]
                acc = detail["account"]
                message += f"  '{pipeline}' - these environments are not in the '{acc}' account: {', '.join(envs)}\n"
            raise ConfigValidatorError(message)

    def validate_environment_pipelines_triggers(self, config):
        errors = []
        pipelines_with_triggers = {
            pipeline_name: pipeline
            for pipeline_name, pipeline in config.get("environment_pipelines", {}).items()
            if "pipeline_to_trigger" in pipeline
        }

        for pipeline_name, pipeline in pipelines_with_triggers.items():
            pipeline_to_trigger = pipeline["pipeline_to_trigger"]
            if pipeline_to_trigger not in config.get("environment_pipelines", {}):
                message = f"  '{pipeline_name}' - '{pipeline_to_trigger}' is not a valid target pipeline to trigger"

                errors.append(message)
                continue

            if pipeline_to_trigger == pipeline_name:
                message = f"  '{pipeline_name}' - pipelines cannot trigger themselves"
                errors.append(message)

        if errors:
            error_message = "The following pipelines are misconfigured: \n"
            raise ConfigValidatorError(error_message + "\n  ".join(errors))

    def validate_database_copy_section(self, config):
        extensions = config.get("extensions", {})
        if not extensions:
            return

        postgres_extensions = {
            key: ext for key, ext in extensions.items() if ext.get("type", None) == "postgres"
        }

        if not postgres_extensions:
            return

        errors = []

        for extension_name, extension in postgres_extensions.items():
            database_copy_sections = extension.get("database_copy", [])

            if not database_copy_sections:
                return

            all_environments = [
                env for env in config.get("environments", {}).keys() if not env == "*"
            ]
            all_envs_string = ", ".join(all_environments)

            for section in database_copy_sections:
                from_env = section["from"]
                to_env = section["to"]

                if from_env == to_env:
                    errors.append(
                        f"database_copy 'to' and 'from' cannot be the same environment in extension '{extension_name}'."
                    )

                if "prod" in to_env:
                    errors.append(
                        f"Copying to a prod environment is not supported: database_copy 'to' cannot be '{to_env}' in extension '{extension_name}'."
                    )

                if from_env not in all_environments:
                    errors.append(
                        f"database_copy 'from' parameter must be a valid environment ({all_envs_string}) but was '{from_env}' in extension '{extension_name}'."
                    )

                if to_env not in all_environments:
                    errors.append(
                        f"database_copy 'to' parameter must be a valid environment ({all_envs_string}) but was '{to_env}' in extension '{extension_name}'."
                    )

        if errors:
            raise ConfigValidatorError("\n".join(errors))

    def validate_database_migration_input_sources(self, config: dict):
        extensions = config.get("extensions", {})
        if not extensions:
            return

        s3_extensions = {
            key: ext for key, ext in extensions.items() if ext.get("type", None) == "s3"
        }

        if not s3_extensions:
            return

        errors = []

        for extension_name, extension in s3_extensions.items():
            for env, env_config in extension.get("environments", {}).items():
                if "data_migration" not in env_config:
                    continue
                data_migration = env_config.get("data_migration", {})
                if "import" in data_migration and "import_sources" in data_migration:
                    errors.append(
                        f"Error in '{extension_name}.environments.{env}.data_migration': only the 'import_sources' property is required - 'import' is deprecated."
                    )
                if "import" not in data_migration and "import_sources" not in data_migration:
                    errors.append(
                        f"'import_sources' property in '{extension_name}.environments.{env}.data_migration' is missing."
                    )
        if errors:
            raise ConfigValidatorError("\n".join(errors))
