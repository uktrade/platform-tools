from pathlib import Path

import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.utils.platform_config import get_environment_pipeline_names
from dbt_platform_helper.utils.platform_config import load_unvalidated_config_file


def test_get_environment_pipeline_names(fakefs, valid_platform_config):
    fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(valid_platform_config))

    names = get_environment_pipeline_names()

    assert {"main", "test", "prod-main"} == names


def test_get_environment_pipeline_names_defaults_to_empty_list_when_theres_no_platform_config_file(
    fakefs,
):
    names = get_environment_pipeline_names()

    assert {} == names


def test_load_unvalidated_config_file_returns_a_dict_given_valid_yaml(fakefs):
    fakefs.create_file(
        Path(PLATFORM_CONFIG_FILE),
        contents="""
test:
    some_key: some_value
""",
    )
    config = load_unvalidated_config_file()

    assert config == {"test": {"some_key": "some_value"}}


def test_load_unvalidated_config_file_returns_empty_dict_given_invalid_yaml(fakefs):
    fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents="{")
    config = load_unvalidated_config_file()

    assert config == {}


def test_get_environment_pipeline_names_returns_empty_dict_given_invalid_yaml(fakefs):
    fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents="{")
    names = get_environment_pipeline_names()
    assert names == {}


def test_get_environment_pipeline_names_given_invalid_config(create_invalid_platform_config_file):
    names = get_environment_pipeline_names()

    assert {"prod-main"} == names
