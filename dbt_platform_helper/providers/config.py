import click
import yaml
from yamllint import config
from yamllint import linter

from dbt_platform_helper.constants import CODEBASE_PIPELINES_KEY
from dbt_platform_helper.constants import ENVIRONMENTS_KEY
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.utils.messages import abort_with_error


class ConfigProvider:
    def __init__(self, config=None):
        self.config = config if config else {}

    def lint_yaml_for_duplicate_keys(self, file_path: str, lint_config=None):
        if lint_config is None:
            lint_config = {"rules": {"key-duplicates": "enable"}}

        yaml_config = config.YamlLintConfig(yaml.dump(lint_config))

        with open(file_path, "r") as yaml_file:
            file_contents = yaml_file.read()
            results = linter.run(file_contents, yaml_config)

        parsed_results = [
            "\t"
            + f"Line {result.line}: {result.message}".replace(" in mapping (key-duplicates)", "")
            for result in results
        ]

        return parsed_results

    def validate_extension_supported_versions(
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

    def get_env_deploy_account_info(config, env, key):
        return (
            config.get("environments", {})
            .get(env, {})
            .get("accounts", {})
            .get("deploy", {})
            .get(key)
        )

    def validate_environment_pipelines(config):
        bad_pipelines = {}
        for pipeline_name, pipeline in config.get("environment_pipelines", {}).items():
            bad_envs = []
            pipeline_account = pipeline.get("account", None)
            if pipeline_account:
                for env in pipeline.get("environments", {}).keys():
                    env_account = ConfigProvider.get_env_deploy_account_info(config, env, "name")
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

    def validate_codebase_pipelines(config):
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

    def validate_environment_pipelines_triggers(config):
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
