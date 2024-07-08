import os
from pathlib import Path

import pytest

from dbt_platform_helper.utils.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.files import config_file_check
from dbt_platform_helper.utils.files import generate_override_files
from dbt_platform_helper.utils.files import is_terraform_project
from dbt_platform_helper.utils.files import mkfile


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


@pytest.mark.parametrize(
    "platform_config_content, expected_result",
    [
        ("application: my-app\nlegacy_project: True", False),
        ("application: my-app\nlegacy_project: False", True),
        ("application: my-app", True),
    ],
)
def test_is_terraform_project(fakefs, platform_config_content, expected_result):
    fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=platform_config_content)

    assert is_terraform_project() == expected_result


@pytest.mark.parametrize(
    "files, expected_messages",
    [
        (
            [],
            [
                f"`{PLATFORM_CONFIG_FILE}` is missing. Please check it exists and you are in the root directory of your deployment project."
            ],
        ),
        (
            ["storage.yml"],
            [
                f"`storage.yml` is no longer supported. Please move its contents into a file named `{PLATFORM_CONFIG_FILE}` under the key 'extensions' and delete `storage.yml`."
            ],
        ),
        (
            ["extensions.yml"],
            [
                f"`extensions.yml` is no longer supported. Please move its contents into a file named `{PLATFORM_CONFIG_FILE}` under the key 'extensions' and delete `extensions.yml`."
            ],
        ),
        (
            ["pipelines.yml"],
            [
                f"`pipelines.yml` is no longer supported. Please move its contents into a file named `{PLATFORM_CONFIG_FILE}`, change the key 'codebases' to 'codebase_pipelines' and delete `pipelines.yml`."
            ],
        ),
        (
            ["storage.yml", "pipelines.yml"],
            [
                f"`storage.yml` is no longer supported. Please move its contents into a file named `{PLATFORM_CONFIG_FILE}` under the key 'extensions' and delete `storage.yml`.",
                f"`pipelines.yml` is no longer supported. Please move its contents into a file named `{PLATFORM_CONFIG_FILE}`, change the key 'codebases' to 'codebase_pipelines' and delete `pipelines.yml`.",
            ],
        ),
        (
            [PLATFORM_CONFIG_FILE, "storage.yml"],
            [
                f"`storage.yml` has been superseded by `{PLATFORM_CONFIG_FILE}` and should be deleted."
            ],
        ),
        (
            [PLATFORM_CONFIG_FILE, "extensions.yml"],
            [
                f"`extensions.yml` has been superseded by `{PLATFORM_CONFIG_FILE}` and should be deleted."
            ],
        ),
        (
            [PLATFORM_CONFIG_FILE, "pipelines.yml"],
            [
                f"`pipelines.yml` has been superseded by `{PLATFORM_CONFIG_FILE}` and should be deleted."
            ],
        ),
        (
            [PLATFORM_CONFIG_FILE, "pipelines.yml", "extensions.yml"],
            [
                f"`pipelines.yml` has been superseded by `{PLATFORM_CONFIG_FILE}` and should be deleted.",
                f"`extensions.yml` has been superseded by `{PLATFORM_CONFIG_FILE}` and should be deleted.",
            ],
        ),
    ],
)
def test_file_compatibility_check_fails_if_platform_config_not_present(
    fakefs, capsys, files, expected_messages
):
    for file in files:
        fakefs.create_file(file)

    with pytest.raises(SystemExit):
        config_file_check()

    console_message = capsys.readouterr().out

    for expected_message in expected_messages:
        assert expected_message in console_message
