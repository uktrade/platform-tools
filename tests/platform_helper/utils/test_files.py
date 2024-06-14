import os
from pathlib import Path

import pytest
import yaml

from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.files import generate_override_files
from dbt_platform_helper.utils.files import is_terraform_project
from dbt_platform_helper.utils.files import load_and_validate_config
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.validation import PLATFORM_CONFIG_SCHEMA
from tests.platform_helper.conftest import FIXTURES_DIR


@pytest.mark.parametrize(
    "schema,yaml_file",
    [
        (PLATFORM_CONFIG_SCHEMA, "pipeline/platform-config.yml"),
        (PLATFORM_CONFIG_SCHEMA, "pipeline/platform-config-with-public-repo.yml"),
        (PLATFORM_CONFIG_SCHEMA, "pipeline/platform-config-for-terraform.yml"),
    ],
)
def test_load_and_validate_config_valid_file(schema, yaml_file):
    """Test that, given the path to a valid yaml file, load_and_validate_config
    returns the loaded yaml unmodified."""

    path = FIXTURES_DIR / yaml_file
    validated = load_and_validate_config(path, schema)

    with open(path, "r") as fd:
        conf = yaml.safe_load(fd)

    assert validated == conf


@pytest.mark.parametrize(
    "file_exists, overwrite, expected",
    [
        (False, False, "File test_file.txt created"),
        (False, True, "File test_file.txt created"),
        (True, True, "File test_file.txt overwritten"),
    ],
)
def test_mkfile_creates_or_overrides_the_file(tmp_path, file_exists, overwrite, expected):
    filename = "test_file.txt"
    file_path = tmp_path / filename
    if file_exists:
        file_path.touch()

    contents = "The content"

    message = mkfile(tmp_path, filename, contents, overwrite)

    assert file_path.exists()
    assert file_path.read_text() == contents
    assert message == expected


def test_mkfile_does_nothing_if_file_already_exists_but_override_is_false(tmp_path):
    filename = "test_file.txt"
    file_path = tmp_path / filename
    file_path.touch()

    message = mkfile(tmp_path, filename, contents="does not matter", overwrite=False)

    assert message == f"File {filename} exists; doing nothing"


def test_generate_override_files(fakefs):
    """Test that, given a path to override files and an output directory,
    generate_override_files copies the required files to the output
    directory."""

    fakefs.create_file("templates/.gitignore")
    fakefs.create_file("templates/bin/code.ts")
    fakefs.create_file("templates/node_modules/package.ts")

    generate_override_files(
        base_path=Path("."), file_path=Path("templates"), output_dir=Path("output")
    )

    assert ".gitignore" in os.listdir("/output")
    assert "code.ts" in os.listdir("/output/bin")
    assert "node_modules" not in os.listdir("/output")


def test_apply_defaults():
    config = {
        "application": "my-app",
        "environments": {
            "*": {"a": "aaa", "b": {"c": "ccc"}},
            "one": None,
            "two": {},
            "three": {"a": "override_aaa", "b": {"d": "ddd"}, "c": "ccc"},
        },
    }

    result = apply_environment_defaults(config)

    assert result == {
        "application": "my-app",
        "environments": {
            "one": {"a": "aaa", "b": {"c": "ccc"}},
            "two": {"a": "aaa", "b": {"c": "ccc"}},
            "three": {"a": "override_aaa", "b": {"d": "ddd"}, "c": "ccc"},
        },
    }


def test_apply_defaults_with_no_defaults():
    config = {
        "application": "my-app",
        "environments": {
            "one": None,
            "two": {},
            "three": {
                "a": "aaa",
            },
        },
    }

    result = apply_environment_defaults(config)

    assert result == {
        "application": "my-app",
        "environments": {"one": {}, "two": {}, "three": {"a": "aaa"}},
    }


@pytest.mark.parametrize("create_terraform_dir", [True, False])
def test_is_terraform_project(fakefs, create_terraform_dir):
    if create_terraform_dir:
        fakefs.create_dir("./terraform")

    assert is_terraform_project() == create_terraform_dir
