from pathlib import Path

import click
import yaml


def load_and_validate_config(path, schema):
    with open(path, "r") as fd:
        conf = yaml.safe_load(fd)

    schema.validate(conf)

    return conf


def to_yaml(value):
    return yaml.dump(value, sort_keys=False)


def mkfile(base_path, file_path, contents, overwrite=False):
    file_exists = (base_path / file_path).exists()

    if file_exists and not overwrite:
        return f"File {file_path} exists; doing nothing"

    action = "overwritten" if file_exists and overwrite else "created"

    with open(base_path / file_path, "w") as fd:
        fd.write(contents)

    return f"File {file_path} {action}"


def ensure_cwd_is_repo_root():
    """Exit if we're not in the root of the repo."""

    if not Path("./copilot").exists() or not Path("./copilot").is_dir():
        click.secho(
            "Cannot find copilot directory. Run this command in the root of the deployment repository.",
            bg="red",
        )
        exit(1)
