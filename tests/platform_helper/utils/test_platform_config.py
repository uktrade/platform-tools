from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.utils.platform_config import (
    get_environment_pipeline_names,
    load_config_file,
    is_terraform_project,
)


def test_load_config_file_returns_a_dict_given_valid_yaml(fakefs):
    fakefs.create_file(
        PLATFORM_CONFIG_FILE,
        contents="""
test:
    some_key: some_value
""",
    )
    config = load_config_file()

    assert config == {"test": {"some_key": "some_value"}}


def test_load_config_file_returns_none_given_invalid_yaml(fakefs):
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents="{")
    config = load_config_file()

    assert config == None


def test_get_environment_pipeline_names(fakefs, valid_platform_config):
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(valid_platform_config))
    names = get_environment_pipeline_names()

    assert {"main", "test", "prod-main"} == names


def test_get_environment_pipeline_names_returns_empty_dict_given_invalid_yaml(fakefs):
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents="{")
    names = get_environment_pipeline_names()
    assert names == {}


def test_get_environment_pipeline_names_given_invalid_config(create_invalid_platform_config_file):
    names = get_environment_pipeline_names()

    assert {"prod-main"} == names


def test_get_environment_pipeline_names_defaults_to_empty_list_when_theres_no_platform_config_file(
    fakefs,
):
    names = get_environment_pipeline_names()

    assert {} == names


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
