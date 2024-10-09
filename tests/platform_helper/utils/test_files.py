import os
from pathlib import Path
from datetime import datetime, timedelta
import yaml

import pytest
from unittest.mock import patch, Mock


from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.files import generate_override_files
from dbt_platform_helper.utils.files import generate_override_files_from_template
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.files import cache_refresh_required, check_if_cached_datetime_is_greater_than_interval, write_to_cache, read_supported_versions_from_cache


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
            "one": {"a": "aaa", "b": {"c": "ccc"}, "versions": {}},
            "two": {"a": "aaa", "b": {"c": "ccc"}, "versions": {}},
            "three": {"a": "override_aaa", "b": {"d": "ddd"}, "c": "ccc", "versions": {}},
        },
    }


@pytest.mark.parametrize(
    "default_versions, env_default_versions, env_versions, expected_result",
    [
        # Empty cases
        (None, None, None, {}),
        (None, None, {}, {}),
        (None, {}, None, {}),
        ({}, None, None, {}),
        # Env versions populated
        (
            None,
            None,
            {"platform-helper": "8.0.0", "terraform-platform-modules": "1.0.0"},
            {"platform-helper": "8.0.0", "terraform-platform-modules": "1.0.0"},
        ),
        (
            None,
            None,
            {"terraform-platform-modules": "2.0.0"},
            {"terraform-platform-modules": "2.0.0"},
        ),
        (None, None, {"platform-helper": "9.0.0"}, {"platform-helper": "9.0.0"}),
        # env_default_versions populated
        (None, {"platform-helper": "10.0.0"}, None, {"platform-helper": "10.0.0"}),
        (None, {"platform-helper": "10.0.0"}, {}, {"platform-helper": "10.0.0"}),
        (
            None,
            {"platform-helper": "10.0.0"},
            {"platform-helper": "8.0.0", "terraform-platform-modules": "1.0.0"},
            {"platform-helper": "8.0.0", "terraform-platform-modules": "1.0.0"},
        ),
        (
            None,
            {"platform-helper": "10.0.0"},
            {"terraform-platform-modules": "2.0.0"},
            {"platform-helper": "10.0.0", "terraform-platform-modules": "2.0.0"},
        ),
        # default_versions populated
        (
            None,
            {"platform-helper": "10.0.0"},
            {"platform-helper": "9.0.0"},
            {"platform-helper": "9.0.0"},
        ),
        (
            {"terraform-platform-modules": "1.0.0"},
            None,
            None,
            {"terraform-platform-modules": "1.0.0"},
        ),
        (
            {"terraform-platform-modules": "2.0.0"},
            {"terraform-platform-modules": "3.0.0"},
            None,
            {"terraform-platform-modules": "3.0.0"},
        ),
        (
            {"terraform-platform-modules": "3.0.0"},
            None,
            {"terraform-platform-modules": "4.0.0"},
            {"terraform-platform-modules": "4.0.0"},
        ),
        (
            {"terraform-platform-modules": "4.0.0"},
            {"terraform-platform-modules": "5.0.0"},
            {"terraform-platform-modules": "6.0.0"},
            {"terraform-platform-modules": "6.0.0"},
        ),
    ],
)
def test_apply_defaults_for_versions(
    default_versions, env_default_versions, env_versions, expected_result
):
    config = {
        "application": "my-app",
        "environments": {"*": {}, "one": {}},
    }
    if default_versions:
        config["default_versions"] = default_versions
    if env_default_versions:
        config["environments"]["*"]["versions"] = env_default_versions
    if env_versions:
        config["environments"]["one"]["versions"] = env_versions

    result = apply_environment_defaults(config)

    assert result["environments"]["one"].get("versions") == expected_result


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
        "environments": {
            "one": {"versions": {}},
            "two": {"versions": {}},
            "three": {"a": "aaa", "versions": {}},
        },
    }


@patch('dbt_platform_helper.utils.files.os.path.exists', return_value=True)
@patch('dbt_platform_helper.utils.files.read_file_as_yaml')
def test_cache_refresh_required_is_true_when_cached_datetime_greater_than_one_day(mock_read_yaml, mock_path_exists):

    read_yaml_return_value = {
        'redis': {
            # Some timestamp which is > than 1 day. i.e. enough to trigger a cache refresh
            'date-retrieved': '09-02-02 10:35:48'
        }
    }
    mock_read_yaml.return_value = read_yaml_return_value

    assert cache_refresh_required('redis')


@patch('dbt_platform_helper.utils.files.os.path.exists', return_value=True)
@patch('dbt_platform_helper.utils.files.read_file_as_yaml')
def test_cache_refresh_required_is_false_when_cached_datetime_less_than_one_day(mock_read_yaml, mock_path_exists):

    today = datetime.now()
    # Time range is still < 1 day so should not require refresh
    middle_of_today = today - timedelta(hours=12)

    read_yaml_return_value = {
        'redis': {
            'date-retrieved': middle_of_today.strftime("%d-%m-%y %H:%M:%S")
        }
    }
    mock_read_yaml.return_value = read_yaml_return_value

    assert not cache_refresh_required('redis')
