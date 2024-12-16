import click
import yaml
from yamllint import config
from yamllint import linter


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
