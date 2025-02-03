from pathlib import Path

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.utils.platform_config import load_unvalidated_config_file


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
