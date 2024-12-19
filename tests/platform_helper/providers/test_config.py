from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.domain.config_validator import ConfigValidator
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.yaml_file_provider import DuplicateKeysException
from dbt_platform_helper.providers.yaml_file_provider import YamlFileProvider
from tests.platform_helper.conftest import FIXTURES_DIR


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
        YamlFileProvider._lint_yaml_for_duplicate_keys(PLATFORM_CONFIG_FILE)

    config_provider = ConfigProvider(ConfigValidator())

    with pytest.raises(SystemExit):
        config_provider.load_and_validate_platform_config(PLATFORM_CONFIG_FILE)

    captured = capsys.readouterr()

    assert expected_error in captured.err


@pytest.mark.parametrize("pipeline_to_trigger", ("", "non-existent-pipeline"))
@patch("dbt_platform_helper.domain.config_validator.abort_with_error")
def test_validate_platform_config_fails_if_pipeline_to_trigger_not_valid(
    mock_abort_with_error, valid_platform_config, pipeline_to_trigger
):
    valid_platform_config["environment_pipelines"]["main"][
        "pipeline_to_trigger"
    ] = pipeline_to_trigger

    config_provider = ConfigProvider(ConfigValidator(), valid_platform_config)

    config_provider.validate_platform_config()
    message = mock_abort_with_error.call_args.args[0]

    assert "The following pipelines are misconfigured:" in message
    assert (
        f"  'main' - '{pipeline_to_trigger}' is not a valid target pipeline to trigger" in message
    )


@patch("dbt_platform_helper.domain.config_validator.abort_with_error")
def test_validate_platform_config_fails_with_multiple_errors_if_pipeline_to_trigger_is_invalid(
    mock_abort_with_error, valid_platform_config
):
    valid_platform_config["environment_pipelines"]["main"]["pipeline_to_trigger"] = ""
    valid_platform_config["environment_pipelines"]["test"][
        "pipeline_to_trigger"
    ] = "non-existent-pipeline"

    config_provider = ConfigProvider(ConfigValidator(), valid_platform_config)

    config_provider.validate_platform_config()
    message = mock_abort_with_error.call_args.args[0]

    assert "The following pipelines are misconfigured:" in message
    assert f"  'main' - '' is not a valid target pipeline to trigger" in message
    assert (
        f"  'test' - 'non-existent-pipeline' is not a valid target pipeline to trigger" in message
    )


@patch("dbt_platform_helper.domain.config_validator.abort_with_error")
def test_validate_platform_config_fails_if_pipeline_to_trigger_is_triggering_itself(
    mock_abort_with_error, valid_platform_config
):
    valid_platform_config["environment_pipelines"]["main"]["pipeline_to_trigger"] = "main"
    config_provider = ConfigProvider(ConfigValidator(), valid_platform_config)
    config_provider.validate_platform_config()
    message = mock_abort_with_error.call_args.args[0]

    assert "The following pipelines are misconfigured:" in message
    assert f"  'main' - pipelines cannot trigger themselves" in message


@pytest.mark.parametrize(
    "account, envs, exp_bad_envs",
    [
        ("account-does-not-exist", ["dev"], ["dev"]),
        ("prod-acc", ["dev", "staging", "prod"], ["dev", "staging"]),
        ("non-prod-acc", ["dev", "prod"], ["prod"]),
    ],
)
@patch("dbt_platform_helper.domain.config_validator.abort_with_error")
def test_validate_platform_config_fails_if_pipeline_account_does_not_match_environment_accounts_with_single_pipeline(
    mock_abort_with_error, platform_env_config, account, envs, exp_bad_envs
):
    platform_env_config["environment_pipelines"] = {
        "main": {
            "account": account,
            "slack_channel": "/codebuild/notification_channel",
            "trigger_on_push": True,
            "environments": {env: {} for env in envs},
        }
    }

    config_provider = ConfigProvider(ConfigValidator(), platform_env_config)

    config_provider.validate_platform_config()

    message = mock_abort_with_error.call_args.args[0]

    assert "The following pipelines are misconfigured:" in message
    assert (
        f"  'main' - these environments are not in the '{account}' account: {', '.join(exp_bad_envs)}"
        in message
    )


@patch("dbt_platform_helper.domain.config_validator.abort_with_error")
def test_validate_platform_config_fails_if_database_copy_config_is_invalid(
    mock_abort_with_error,
):
    """Edge cases for this are all covered in unit tests of
    validate_database_copy_section elsewhere in this file."""
    config = {
        "application": "test-app",
        "environments": {"dev": {}, "test": {}, "prod": {}},
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "dev", "to": "dev"}],
            }
        },
    }

    config_provider = ConfigProvider(ConfigValidator(), config)

    config_provider.validate_platform_config()

    message = mock_abort_with_error.call_args.args[0]

    assert (
        f"database_copy 'to' and 'from' cannot be the same environment in extension 'our-postgres'."
        in message
    )


@patch("dbt_platform_helper.domain.config_validator.abort_with_error")
def test_validate_platform_config_catches_database_copy_errors(
    mock_abort_with_error, platform_env_config
):
    platform_env_config["environment_pipelines"] = {
        "main": {
            "account": "non-prod",
            "slack_channel": "/codebuild/notification_channel",
            "trigger_on_push": True,
            "environments": {"dev": {}, "prod": {}},
        },
        "prod": {
            "account": "prod",
            "slack_channel": "/codebuild/notification_channel",
            "trigger_on_push": True,
            "environments": {"dev": {}, "staging": {}, "prod": {}},
        },
    }

    config_provider = ConfigProvider(ConfigValidator(), platform_env_config)

    config_provider.validate_platform_config()

    message = mock_abort_with_error.call_args.args[0]

    assert "The following pipelines are misconfigured:" in message
    assert f"  'main' - these environments are not in the 'non-prod' account: dev" in message
    assert f"  'prod' - these environments are not in the 'prod' account: dev, staging" in message


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
    config_provider = ConfigProvider(ConfigValidator(), platform_env_config)

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

    config_provider = ConfigProvider(ConfigValidator())

    path = FIXTURES_DIR / yaml_file
    validated = config_provider.load_and_validate_platform_config(path=path)

    with open(path, "r") as fd:
        conf = yaml.safe_load(fd)

    assert validated == conf


def test_validation_fails_if_invalid_default_version_keys_present(
    fakefs, capsys, valid_platform_config
):
    valid_platform_config["default_versions"] = {"something-invalid": "1.2.3"}
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(valid_platform_config))

    config_provider = ConfigProvider(ConfigValidator(), valid_platform_config)

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
    config_provider = ConfigProvider(ConfigValidator(), valid_platform_config)

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
    config_provider = ConfigProvider(ConfigValidator(), valid_platform_config)

    with pytest.raises(SystemExit) as ex:
        config_provider.load_and_validate_platform_config()

        assert f"Wrong key '{invalid_key}'" in str(ex)


def test_load_and_validate_platform_config_fails_with_invalid_yaml(fakefs, capsys):
    """Test that, given the path to an invalid yaml file,
    load_and_validate_config aborts and prints an error."""

    Path(PLATFORM_CONFIG_FILE).write_text("{invalid data")
    with pytest.raises(SystemExit):
        ConfigProvider(ConfigValidator()).load_and_validate_platform_config()

    assert f"{PLATFORM_CONFIG_FILE} is not valid YAML" in capsys.readouterr().err


def test_validation_runs_against_platform_config_yml(fakefs):
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents='{"application": "my_app"}')
    config = ConfigProvider(ConfigValidator()).load_and_validate_platform_config(
        path=PLATFORM_CONFIG_FILE
    )

    assert list(config.keys()) == ["application"]
    assert config["application"] == "my_app"


def test_aws_validation_can_be_switched_off(s3_extensions_fixture, capfd):
    config_provider = ConfigProvider(ConfigValidator())
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

    config_provider = ConfigProvider(Mock(), config=config)
    result = config_provider.apply_environment_defaults()

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
    config_provider = ConfigProvider(Mock(), config=config)

    result = config_provider.apply_environment_defaults()

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
    config_provider = ConfigProvider(Mock(), config=config)

    result = config_provider.apply_environment_defaults()

    assert result == {
        "application": "my-app",
        "environments": {
            "one": {"versions": {}},
            "two": {"versions": {}},
            "three": {"a": "aaa", "versions": {}},
        },
    }
