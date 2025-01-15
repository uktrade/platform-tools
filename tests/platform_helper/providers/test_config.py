import os
import re
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from dbt_platform_helper.constants import CODEBASE_PIPELINES_KEY
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.yaml_file import DuplicateKeysException
from dbt_platform_helper.providers.yaml_file import YamlFileProvider
from tests.platform_helper.conftest import FIXTURES_DIR


def mock_validator():
    return Mock()


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

    with pytest.raises(DuplicateKeysException, match=expected_error):
        YamlFileProvider.lint_yaml_for_duplicate_keys(PLATFORM_CONFIG_FILE)


@pytest.mark.parametrize(
    "account, envs",
    [
        ("non-prod-acc", ["dev", "staging"]),
        ("prod-acc", ["prod"]),
    ],
)
def test_validate_platform_config_succeeds_if_pipeline_account_matches_environment_accounts(
    platform_env_config, account, envs
):
    platform_env_config["environment_pipelines"] = {
        "main": {
            "account": account,
            "slack_channel": "/codebuild/notification_channel",
            "trigger_on_push": True,
            "environments": {env: {} for env in envs},
        }
    }

    # Should not error if config is sound.
    config_provider = ConfigProvider(mock_validator())
    config_provider.config = platform_env_config

    config_provider.validate_platform_config()


@pytest.mark.parametrize(
    "yaml_file",
    [
        "pipeline/platform-config.yml",
        "pipeline/platform-config-with-public-repo.yml",
        "pipeline/platform-config-for-terraform.yml",
    ],
)
def test_load_and_validate_config_valid_file(yaml_file):
    """Test that, given the path to a valid yaml file, load_and_validate_config
    returns the loaded yaml unmodified."""

    config_provider = ConfigProvider(mock_validator())

    path = FIXTURES_DIR / yaml_file
    validated = config_provider.load_and_validate_platform_config(path=path)

    with open(path, "r") as fd:
        conf = yaml.safe_load(fd)

    assert validated == conf


def test_get_enriched_config_returns_config_with_environment_defaults_applied():
    mock_file_provider = Mock(spec=FileProvider)
    mock_file_provider.load.return_value = {
        "application": "test-app",
        "environments": {
            "*": {
                "vpc": "vpc3",
                "accounts": {
                    "deploy": {"name": "non-prod-acc", "id": "1122334455"},
                    "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
                },
            },
            "test": {"versions": {"terraform-platform-modules": "123456"}},
        },
    }

    expected_enriched_config_config = {
        "application": "test-app",
        "environments": {
            "test": {
                "vpc": "vpc3",
                "accounts": {
                    "deploy": {"name": "non-prod-acc", "id": "1122334455"},
                    "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
                },
                "versions": {"terraform-platform-modules": "123456"},
            }
        },
    }

    mock_config_validator = Mock()

    result = ConfigProvider(mock_config_validator, mock_file_provider).get_enriched_config()
    assert result == expected_enriched_config_config


def test_validation_fails_if_invalid_default_version_keys_present(
    fakefs, capsys, valid_platform_config
):
    valid_platform_config["default_versions"] = {"something-invalid": "1.2.3"}
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(valid_platform_config))

    config_provider = ConfigProvider(mock_validator())
    config_provider.config = valid_platform_config

    with pytest.raises(SystemExit) as ex:
        config_provider.load_and_validate_platform_config()

        assert "Wrong key 'something-invalid'" in str(ex)


@pytest.mark.parametrize(
    "invalid_key",
    (
        "",
        "invalid-key",
        "platform-helper",  # platform-helper is not valid in the environment overrides.
    ),
)
def test_validation_fails_if_invalid_environment_version_override_keys_present(
    invalid_key, fakefs, capsys, valid_platform_config
):
    valid_platform_config["environments"]["*"]["versions"] = {invalid_key: "1.2.3"}
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(valid_platform_config))
    config_provider = ConfigProvider(mock_validator())
    config_provider.config = valid_platform_config

    with pytest.raises(SystemExit) as ex:
        config_provider.load_and_validate_platform_config()

        assert f"Wrong key '{invalid_key}'" in str(ex)


@pytest.mark.parametrize(
    "invalid_key",
    (
        "",
        "invalid-key",
        "terraform-platform-modules",  # terraform-platform-modules is not valid in the pipeline overrides.
    ),
)
def test_validation_fails_if_invalid_pipeline_version_override_keys_present(
    invalid_key, fakefs, capsys, valid_platform_config
):
    valid_platform_config["environment_pipelines"]["test"]["versions"][invalid_key] = "1.2.3"
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(valid_platform_config))
    config_provider = ConfigProvider(mock_validator())

    with pytest.raises(SystemExit) as ex:
        config_provider.load_and_validate_platform_config()

        assert f"Wrong key '{invalid_key}'" in str(ex)


def test_load_and_validate_platform_config_fails_with_invalid_yaml(fakefs, capsys):
    """Test that, given the path to an invalid yaml file,
    load_and_validate_config aborts and prints an error."""

    Path(PLATFORM_CONFIG_FILE).write_text("{invalid data")
    with pytest.raises(SystemExit):
        ConfigProvider(mock_validator()).load_and_validate_platform_config()

    assert f"{PLATFORM_CONFIG_FILE} is not valid YAML" in capsys.readouterr().err


def test_load_and_validate_platform_config_fails_with_missing_config_file(fakefs, capsys):
    if Path(PLATFORM_CONFIG_FILE).exists():
        os.remove(Path(PLATFORM_CONFIG_FILE))

    with pytest.raises(SystemExit):
        ConfigProvider(mock_validator()).load_and_validate_platform_config()

    assert (
        f"`{PLATFORM_CONFIG_FILE}` is missing. Please check it exists and you are in the root directory of your deployment project."
        in capsys.readouterr().err
    )


def test_validation_runs_against_platform_config_yml(fakefs):
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents='{"application": "my_app"}')
    config = ConfigProvider(mock_validator()).load_and_validate_platform_config(
        path=PLATFORM_CONFIG_FILE
    )

    assert list(config.keys()) == ["application"]
    assert config["application"] == "my_app"


def test_aws_validation_can_be_switched_off(s3_extensions_fixture, capfd):
    config_provider = ConfigProvider(mock_validator())
    config_provider.load_and_validate_platform_config()

    assert "Warning" not in capfd.readouterr().out


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

    result = ConfigProvider.apply_environment_defaults(config)

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

    result = ConfigProvider.apply_environment_defaults(config)

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

    result = ConfigProvider.apply_environment_defaults(config)

    assert result == {
        "application": "my-app",
        "environments": {
            "one": {"versions": {}},
            "two": {"versions": {}},
            "three": {"a": "aaa", "versions": {}},
        },
    }


def test_codebase_pipeline_run_groups_validate(fakefs, capsys):
    platform_config = {
        "application": "test-app",
        "codebase_pipelines": [
            {
                "name": "application",
                "repository": "organisation/repository",
                "services": [
                    {"run_group_1": ["web"]},
                    {"run_group_2": ["api", "celery-beat"]},
                ],
                "pipelines": [
                    {"name": "main", "branch": "main", "environments": [{"name": "dev"}]}
                ],
            }
        ],
    }
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(platform_config))

    config = ConfigProvider(mock_validator()).load_and_validate_platform_config()

    assert config[CODEBASE_PIPELINES_KEY][0]["services"] == [
        {"run_group_1": ["web"]},
        {"run_group_2": ["api", "celery-beat"]},
    ]


def test_codebase_slack_channel_fails_if_not_a_string(fakefs, capsys):
    channel = 1
    config = {
        "application": "test-app",
        "codebase_pipelines": [
            {
                "name": "application",
                "slack_channel": channel,
                "repository": "organisation/repository",
                "services": [],
                "pipelines": [],
            }
        ],
    }
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(config))

    with pytest.raises(SystemExit):
        ConfigProvider(mock_validator()).load_and_validate_platform_config()

    exp = ".*Key 'slack_channel' error:.*1 should be instance of 'str'.*"
    assert re.match(exp, capsys.readouterr().err, re.DOTALL)
