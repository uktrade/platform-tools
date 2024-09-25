from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.utils.platform_config import (
    get_environment_pipeline_names,
    load_config,
    is_terraform_project,
)


def test_get_environment_pipeline_names(create_valid_platform_config_file):
    names = get_environment_pipeline_names()

    assert {"main", "test", "prod-main"} == names


@patch("dbt_platform_helper.utils.platform_config.load_config")
def test_get_environment_pipeline_names_returns_empty_dict_if_platform_config_is_invalid_yaml(
    mock_config,
):
    mock_config.return_value = "{"
    names = get_environment_pipeline_names()
    assert names == {}


def test_get_environment_pipeline_names_with_invalid_config(create_invalid_platform_config_file):
    names = get_environment_pipeline_names()

    assert {"prod-main"} == names


def test_get_environment_pipeline_names_defaults_to_empty_list_when_theres_no_platform_config(
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
