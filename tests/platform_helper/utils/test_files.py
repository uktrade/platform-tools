import os
from pathlib import Path

import pytest

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.files import generate_override_files
from dbt_platform_helper.utils.files import generate_override_files_from_template
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


def test_generate_pipeline_override_files(fakefs):
    """Test that generate_pipeline_override_files copies and renders the
    required files along with templated data to the output directory."""

    fakefs.create_file("templates/.gitignore", contents="This is the .gitignore template.")
    fakefs.create_file("templates/bin/code.ts", contents="This is the code.ts template.")
    fakefs.create_file(
        "templates/node_modules/package.ts", contents="This is the package.ts template."
    )
    fakefs.create_file(
        "templates/buildspec.deploy.yml", contents="Contains {{ environments }} environments."
    )

    template_data = {"environments": [{"name": "dev"}, {"name": "prod"}]}

    generate_override_files_from_template(
        base_path=Path("."),
        overrides_path=Path("templates"),
        output_dir=Path("output"),
        template_data=template_data,
    )

    assert os.path.isfile("output/.gitignore")
    assert os.path.isfile("output/bin/code.ts")
    assert not os.path.exists("output/node_modules")

    with open("output/.gitignore", "r") as f:
        assert f.read() == "This is the .gitignore template."

    with open("output/bin/code.ts", "r") as f:
        assert f.read() == "This is the code.ts template."

    with open("output/buildspec.deploy.yml", "r") as f:
        assert f.read() == "Contains dev,prod environments."


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


@pytest.mark.parametrize(
    "env_config, expected_result",
    [
        (None, {"platform-helper": "10.0.0"}),
        ({}, {"platform-helper": "10.0.0"}),
        (
            {"versions": {"platform-helper": "8.0.0", "terraform-platform-modules": "1.0.0"}},
            {"platform-helper": "8.0.0", "terraform-platform-modules": "1.0.0"},
        ),
        (
            {"versions": {"terraform-platform-modules": "2.0.0"}},
            {"platform-helper": "10.0.0", "terraform-platform-modules": "2.0.0"},
        ),
        ({"versions": {"platform-helper": "9.0.0"}}, {"platform-helper": "9.0.0"}),
    ],
)
def test_apply_defaults_for_versions(env_config, expected_result):
    config = {
        "application": "my-app",
        "environments": {"*": {"versions": {"platform-helper": "10.0.0"}}, "one": env_config},
    }

    result = apply_environment_defaults(config)

    assert result["environments"]["one"]["versions"] == expected_result


def test_apply_defaults_when_versions_missing():
    config = {
        "application": "my-app",
        "environments": {"*": {}, "one": {}},
    }

    result = apply_environment_defaults(config)

    assert result["environments"]["one"] == {}


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
