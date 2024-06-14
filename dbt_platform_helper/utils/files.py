from copy import deepcopy
from os import makedirs
from pathlib import Path

import click
import yaml

PLATFORM_CONFIG_FILE = "platform-config.yml"


def file_compatibility_check():
    platform_config_exists = Path(PLATFORM_CONFIG_FILE).exists()
    qualifier = "" if platform_config_exists else "a file "
    errors = []

    if Path("storage.yml").exists():
        errors.append(
            f"`storage.yml` is no longer supported. Please move into {qualifier}`{PLATFORM_CONFIG_FILE}` under the key `extensions` and delete `storage.yml`."
        )

    if Path("extensions.yml").exists():
        errors.append(
            f"`extensions.yml` is no longer supported. Please move the contents into {qualifier}`{PLATFORM_CONFIG_FILE}` and delete `extensions.yml`."
        )

    if Path("pipelines.yml").exists():
        errors.append(
            f"`pipelines.yml` is no longer supported. Please move the contents into {qualifier}`{PLATFORM_CONFIG_FILE}`, change the key 'codebases' to 'codebase_pipelines' and delete `pipelines.yml`."
        )

    if errors:
        click.secho("\n".join(errors), bg="red")
        exit(1)


def load_and_validate_config(path, schema):
    conf = yaml.safe_load(Path(path).read_text())

    schema.validate(conf)

    return conf


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


def ensure_cwd_is_repo_root():
    """Exit if we're not in the root of the repo."""

    if not Path("./copilot").exists() or not Path("./copilot").is_dir():
        click.secho(
            "Cannot find copilot directory. Run this command in the root of the deployment repository.",
            bg="red",
        )
        exit(1)


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
    return Path("./terraform").is_dir()
