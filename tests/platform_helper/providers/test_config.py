from pathlib import Path

import pytest
import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.utils.validation import load_and_validate_platform_config


def test_lint_yaml_for_duplicate_keys_fails_when_duplicate_keys_provided(
    valid_platform_config, fakefs, capsys
):
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(valid_platform_config))

    # Remove the extensions key-value pair from the platform config - re-added as plain text.
    valid_platform_config.pop("extensions")

    duplicate_key = "duplicate-key"
    duplicate_extension = f"""
  {duplicate_key}:
    type: redis
    environments:
      "*":
        engine: '7.1'
        plan: tiny
        apply_immediately: true
"""

    # Combine the valid config (minus the extensions key) and the duplicate key config
    invalid_platform_config = f"""
{yaml.dump(valid_platform_config)}
extensions:
{duplicate_extension}
{duplicate_extension}
"""

    Path(PLATFORM_CONFIG_FILE).write_text(invalid_platform_config)
    expected_error = f'duplication of key "{duplicate_key}"'

    config_provider = ConfigProvider()

    linting_failures = config_provider.lint_yaml_for_duplicate_keys(PLATFORM_CONFIG_FILE)
    assert expected_error in linting_failures[0]

    with pytest.raises(SystemExit) as excinfo:
        load_and_validate_platform_config(PLATFORM_CONFIG_FILE)

    captured = capsys.readouterr()

    assert expected_error in captured.err
    assert excinfo.value.code == 1
