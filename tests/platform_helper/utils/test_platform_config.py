from pathlib import Path

import pytest
import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.utils.platform_config import get_environment_pipeline_names
from dbt_platform_helper.utils.platform_config import (
    is_s3_bucket_data_migration_enabled,
)
from dbt_platform_helper.utils.platform_config import is_terraform_project


def test_get_environment_pipeline_names(fakefs, valid_platform_config):
    fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(valid_platform_config))

    names = get_environment_pipeline_names()

    assert {"main", "test", "prod-main"} == names


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


def test_is_s3_bucket_data_migration_enabled(fakefs, valid_platform_config):
    fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(valid_platform_config))

    assert is_s3_bucket_data_migration_enabled("s3-data-migration")


def test_is_s3_bucket_data_migration_not_enabled(fakefs, valid_platform_config):
    fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(valid_platform_config))

    assert not is_s3_bucket_data_migration_enabled("test-app-s3-bucket")
