from typing import Callable

import boto3
import click

from dbt_platform_helper.constants import CODEBASE_PIPELINES_KEY
from dbt_platform_helper.constants import ENVIRONMENTS_KEY
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.providers.opensearch import OpensearchProvider
from dbt_platform_helper.providers.redis import RedisProvider
from dbt_platform_helper.utils.messages import abort_with_error


class ConfigValidator:

    def __init__(self, validations: Callable[[dict], None] = None):
        self.validations = validations or [
            self.validate_supported_redis_versions,
            self.validate_supported_opensearch_versions,
            self.validate_environment_pipelines,
            self.validate_codebase_pipelines,
            self.validate_environment_pipelines_triggers,
            self.validate_database_copy_section,
        ]

    def run_validations(self, config: dict):
        for validation in self.validations:
            validation(config)

    def _validate_extension_supported_versions(
        self, config, extension_type, version_key, get_supported_versions
    ):
        extensions = config.get("extensions", {})
        if not extensions:
            return

        extensions_for_type = [
            extension
            for extension in config.get("extensions", {}).values()
            if extension.get("type") == extension_type
        ]

        supported_extension_versions = get_supported_versions()
        extensions_with_invalid_version = []

        for extension in extensions_for_type:

            environments = extension.get("environments", {})

            if not isinstance(environments, dict):
                click.secho(
                    f"Error: {extension_type} extension definition is invalid type, expected dictionary",
                    fg="red",
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
            click.secho(
                f"{extension_type} version for environment {version_failure['environment']} is not in the list of supported {extension_type} versions: {supported_extension_versions}. Provided Version: {version_failure['version']}",
                fg="red",
            )

    def validate_supported_redis_versions(self, config):
        return self._validate_extension_supported_versions(
            config=config,
            extension_type="redis",
            version_key="engine",
            get_supported_versions=RedisProvider(
                boto3.client("elasticache")
            ).get_supported_redis_versions,
        )

    def validate_supported_opensearch_versions(self, config):
        return self._validate_extension_supported_versions(
            config=config,
            extension_type="opensearch",
            version_key="engine",
            get_supported_versions=OpensearchProvider(
                boto3.client("opensearch")
            ).get_supported_opensearch_versions,
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
            abort_with_error(message)

    def validate_codebase_pipelines(self, config):
        if CODEBASE_PIPELINES_KEY in config:
            for codebase in config[CODEBASE_PIPELINES_KEY]:
                codebase_environments = []

                for pipeline in codebase["pipelines"]:
                    codebase_environments += [e["name"] for e in pipeline[ENVIRONMENTS_KEY]]

                unique_codebase_environments = sorted(list(set(codebase_environments)))

                if sorted(codebase_environments) != sorted(unique_codebase_environments):
                    abort_with_error(
                        f"The {PLATFORM_CONFIG_FILE} file is invalid, each environment can only be "
                        "listed in a single pipeline per codebase"
                    )

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
            abort_with_error(error_message + "\n  ".join(errors))

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

                from_account = (
                    config.get("environments", {})
                    .get(from_env, {})
                    .get("accounts", {})
                    .get("deploy", {})
                    .get("id")
                )
                to_account = (
                    config.get("environments", {})
                    .get(to_env, {})
                    .get("accounts", {})
                    .get("deploy", {})
                    .get("id")
                )

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

                if from_account != to_account:
                    if "from_account" not in section:
                        errors.append(
                            f"Environments '{from_env}' and '{to_env}' are in different AWS accounts. The 'from_account' parameter must be present."
                        )
                    elif section["from_account"] != from_account:
                        errors.append(
                            f"Incorrect value for 'from_account' for environment '{from_env}'"
                        )

                    if "to_account" not in section:
                        errors.append(
                            f"Environments '{from_env}' and '{to_env}' are in different AWS accounts. The 'to_account' parameter must be present."
                        )
                    elif section["to_account"] != to_account:
                        errors.append(
                            f"Incorrect value for 'to_account' for environment '{to_env}'"
                        )

        if errors:
            abort_with_error("\n".join(errors))
