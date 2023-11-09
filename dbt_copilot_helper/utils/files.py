from os import makedirs
from pathlib import Path

import click
import yaml


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
