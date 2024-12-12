import os
import re
from pathlib import Path

import boto3
import click
import yaml
from schema import SchemaError
from yaml.parser import ParserError
from yamllint import config
from yamllint import linter

from dbt_platform_helper.constants import CODEBASE_PIPELINES_KEY
from dbt_platform_helper.constants import ENVIRONMENTS_KEY
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.providers.platform_config_schema import EXTENSION_SCHEMAS
from dbt_platform_helper.providers.platform_config_schema import PLATFORM_CONFIG_SCHEMA
from dbt_platform_helper.providers.redis import RedisProvider
from dbt_platform_helper.utils.aws import get_supported_opensearch_versions
from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.messages import abort_with_error


def validate_addons(addons: dict):
    """
    Validate the addons file and return a dictionary of addon: error message.
    """
    errors = {}

    for addon_name, addon in addons.items():
        try:
            addon_type = addon.get("type", None)
            if not addon_type:
                errors[addon_name] = f"Missing addon type in addon '{addon_name}'"
                continue
            schema = EXTENSION_SCHEMAS.get(addon_type, None)
            if not schema:
                errors[addon_name] = (
                    f"Unsupported addon type '{addon_type}' in addon '{addon_name}'"
                )
                continue
            schema.validate(addon)
        except SchemaError as ex:
            errors[addon_name] = f"Error in {addon_name}: {ex.code}"

    _validate_extension_supported_versions(
        config={"extensions": addons},
        extension_type="redis",
        version_key="engine",
        get_supported_versions=get_supported_redis_versions,
    )
    _validate_extension_supported_versions(
        config={"extensions": addons},
        extension_type="opensearch",
        version_key="engine",
        get_supported_versions=get_supported_opensearch_versions,
    )

    return errors


def float_between_with_halfstep(lower, upper):
    def is_between(value):
        is_number = isinstance(value, int) or isinstance(value, float)
        is_half_step = re.match(r"^\d+(\.[05])?$", str(value))

        if is_number and is_half_step and lower <= value <= upper:
            return True
        raise SchemaError(f"should be a number between {lower} and {upper} in increments of 0.5")

    return is_between


def validate_platform_config(config):
    PLATFORM_CONFIG_SCHEMA.validate(config)
    enriched_config = apply_environment_defaults(config)
    _validate_environment_pipelines(enriched_config)
    _validate_environment_pipelines_triggers(enriched_config)
    _validate_codebase_pipelines(enriched_config)
    validate_database_copy_section(enriched_config)

    _validate_extension_supported_versions(
        config=config,
        extension_type="redis",
        version_key="engine",
        get_supported_versions=RedisProvider(
            boto3.client("elasticache")
        ).get_supported_redis_versions,
    ),
    _validate_extension_supported_versions(
        config=config,
        extension_type="opensearch",
        version_key="engine",
        get_supported_versions=get_supported_opensearch_versions,
    )


def _validate_extension_supported_versions(
    config, extension_type, version_key, get_supported_versions
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


def validate_database_copy_section(config):
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

        all_environments = [env for env in config.get("environments", {}).keys() if not env == "*"]
        all_envs_string = ", ".join(all_environments)

        for section in database_copy_sections:
            from_env = section["from"]
            to_env = section["to"]

            from_account = _get_env_deploy_account_info(config, from_env, "id")
            to_account = _get_env_deploy_account_info(config, to_env, "id")

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
                    errors.append(f"Incorrect value for 'to_account' for environment '{to_env}'")

    if errors:
        abort_with_error("\n".join(errors))


def _get_env_deploy_account_info(config, env, key):
    return (
        config.get("environments", {}).get(env, {}).get("accounts", {}).get("deploy", {}).get(key)
    )


def _validate_environment_pipelines(config):
    bad_pipelines = {}
    for pipeline_name, pipeline in config.get("environment_pipelines", {}).items():
        bad_envs = []
        pipeline_account = pipeline.get("account", None)
        if pipeline_account:
            for env in pipeline.get("environments", {}).keys():
                env_account = _get_env_deploy_account_info(config, env, "name")
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


def _validate_codebase_pipelines(config):
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


def _validate_environment_pipelines_triggers(config):
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


def lint_yaml_for_duplicate_keys(file_path):
    lint_yaml_config = """
rules:
  key-duplicates: enable
"""
    yaml_config = config.YamlLintConfig(lint_yaml_config)

    with open(file_path, "r") as yaml_file:
        file_contents = yaml_file.read()
        results = linter.run(file_contents, yaml_config)

    parsed_results = [
        "\t" + f"Line {result.line}: {result.message}".replace(" in mapping (key-duplicates)", "")
        for result in results
    ]

    return parsed_results


def load_and_validate_platform_config(path=PLATFORM_CONFIG_FILE, disable_file_check=False):
    if not disable_file_check:
        config_file_check(path)
    try:
        conf = yaml.safe_load(Path(path).read_text())
        duplicate_keys = lint_yaml_for_duplicate_keys(path)
        if duplicate_keys:
            abort_with_error(
                "Duplicate keys found in platform-config:"
                + os.linesep
                + os.linesep.join(duplicate_keys)
            )
        validate_platform_config(conf)
        return conf
    except ParserError:
        abort_with_error(f"{PLATFORM_CONFIG_FILE} is not valid YAML")
    except SchemaError as e:
        abort_with_error(f"Schema error in {PLATFORM_CONFIG_FILE}. {e}")


def config_file_check(path=PLATFORM_CONFIG_FILE):
    platform_config_exists = Path(path).exists()
    errors = []
    warnings = []

    messages = {
        "storage.yml": {"instruction": " under the key 'extensions'", "type": errors},
        "extensions.yml": {"instruction": " under the key 'extensions'", "type": errors},
        "pipelines.yml": {
            "instruction": ", change the key 'codebases' to 'codebase_pipelines'",
            "type": errors,
        },
        PLATFORM_HELPER_VERSION_FILE: {
            "instruction": ", under the key `default_versions: platform-helper:`",
            "type": warnings,
        },
    }

    for file in messages.keys():
        if Path(file).exists():
            message = (
                f"`{file}` is no longer supported. Please move its contents into the "
                f"`{PLATFORM_CONFIG_FILE}` file{messages[file]['instruction']} and delete `{file}`."
            )
            messages[file]["type"].append(message)

    if not errors and not warnings and not platform_config_exists:
        errors.append(
            f"`{PLATFORM_CONFIG_FILE}` is missing. "
            "Please check it exists and you are in the root directory of your deployment project."
        )

    if warnings:
        click.secho("\n".join(warnings), bg="yellow", fg="black")
    if errors:
        click.secho("\n".join(errors), bg="red", fg="white")
        exit(1)
