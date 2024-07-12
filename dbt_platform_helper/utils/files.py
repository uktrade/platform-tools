from copy import deepcopy
from os import makedirs
from pathlib import Path

import click
import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE

CONFIG_FILE_MESSAGES = {
    "storage.yml": " under the key 'extensions'",
    "extensions.yml": " under the key 'extensions'",
    "pipelines.yml": ", change the key 'codebases' to 'codebase_pipelines'",
}


def to_yaml(value):
    return yaml.dump(value, sort_keys=False)


def mkfile(base_path, file_path, contents, overwrite=False):
    file_path = Path(file_path)
    file = Path(base_path).joinpath(file_path)
    file_exists = file.exists()

    if not file_path.parent.exists():
        makedirs(file_path.parent)

    if file_exists and not overwrite:
        return f"File {file_path} exists; doing nothing"

    action = "overwritten" if file_exists and overwrite else "created"

    file.write_text(contents)

    return f"File {file_path} {action}"


def generate_override_files(base_path, file_path, output_dir):
    def generate_files_for_dir(pattern):
        for file in file_path.glob(pattern):
            if file.is_file():
                contents = file.read_text()
                file_name = str(file).removeprefix(f"{file_path}/")
                click.echo(
                    mkfile(
                        base_path,
                        output_dir / file_name,
                        contents,
                        overwrite=True,
                    )
                )

    generate_files_for_dir("*")
    generate_files_for_dir("bin/*")


def apply_environment_defaults(config):
    if "environments" not in config:
        return config

    enriched_config = deepcopy(config)

    environments = enriched_config["environments"]
    env_defaults = environments.get("*", {})
    without_defaults_entry = {
        name: data if data else {} for name, data in environments.items() if name != "*"
    }
    defaulted_envs = {
        name: {**env_defaults, **data} for name, data in without_defaults_entry.items()
    }

    enriched_config["environments"] = defaulted_envs

    return enriched_config


def is_terraform_project() -> bool:
    config = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    return not config.get("legacy_project", False)
