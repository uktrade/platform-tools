from unittest.mock import MagicMock

import pytest

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.domain.config_validator import ConfigValidator
from dbt_platform_helper.providers.config import ConfigProvider


@pytest.mark.parametrize(
    "database_copy_section",
    [
        None,
        [{"from": "dev", "to": "test"}],
        [{"from": "test", "to": "dev"}],
        [
            {
                "from": "prod",
                "to": "test",
                "from_account": "9999999999",
                "to_account": "1122334455",
            }
        ],
        [
            {
                "from": "dev",
                "to": "test",
                "from_account": "9999999999",
                "to_account": "9999999999",
            }
        ],
        [{"from": "test", "to": "dev", "pipeline": {}}],
        [{"from": "test", "to": "dev", "pipeline": {"schedule": "0 0 * * WED"}}],
        [
            {
                "from": "test",
                "to": "dev",
                "from_account": "9999999999",
                "to_account": "1122334455",
                "pipeline": {"schedule": "0 0 * * WED"},
            }
        ],
    ],
)
def test_validate_database_copy_section_success_cases(database_copy_section):
    config = {
        "application": "test-app",
        "environments": {
            "dev": {"accounts": {"deploy": {"id": "1122334455"}}},
            "test": {"accounts": {"deploy": {"id": "1122334455"}}},
            "prod": {"accounts": {"deploy": {"id": "9999999999"}}},
        },
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
            }
        },
    }

    if database_copy_section:
        config["extensions"]["our-postgres"]["database_copy"] = database_copy_section

    ConfigValidator().validate_database_copy_section(config)

    # Should get here fine if the config is valid.


@pytest.mark.parametrize(
    "database_copy_section, expected_parameters",
    [
        ([{"from": "hotfix", "to": "test"}], ["from"]),
        ([{"from": "dev", "to": "hotfix"}], ["to"]),
        ([{"from": "hotfix", "to": "hotfix"}], ["to", "from"]),
        ([{"from": "test", "to": "dev"}, {"from": "dev", "to": "hotfix"}], ["to"]),
        ([{"from": "hotfix", "to": "test"}, {"from": "dev", "to": "test"}], ["from"]),
    ],
)
def test_validate_database_copy_section_failure_cases(
    capsys, database_copy_section, expected_parameters
):
    config = {
        "application": "test-app",
        "environments": {"dev": {}, "test": {}, "prod": {}},
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
            }
        },
    }

    config["extensions"]["our-postgres"]["database_copy"] = database_copy_section

    with pytest.raises(SystemExit):
        ConfigValidator().validate_database_copy_section(config)

    console_message = capsys.readouterr().err

    for param in expected_parameters:
        msg = f"database_copy '{param}' parameter must be a valid environment (dev, test, prod) but was 'hotfix' in extension 'our-postgres'."
        assert msg in console_message


def test_validate_database_copy_fails_if_from_and_to_are_the_same(capsys):
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

    with pytest.raises(SystemExit):
        ConfigValidator().validate_database_copy_section(config)

    console_message = capsys.readouterr().err

    msg = (
        f"database_copy 'to' and 'from' cannot be the same environment in extension 'our-postgres'."
    )
    assert msg in console_message


@pytest.mark.parametrize(
    "env_name",
    ["prod", "prod-env", "env-that-is-prod", "thing-prod-thing"],
)
def test_validate_database_copy_section_fails_if_the_to_environment_is_prod(capsys, env_name):
    config = {
        "application": "test-app",
        "environments": {"dev": {}, "test": {}, "prod": {}},
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "dev", "to": env_name}],
            }
        },
    }

    with pytest.raises(SystemExit):
        ConfigValidator().validate_database_copy_section(config)

    console_message = capsys.readouterr().err

    msg = f"Copying to a prod environment is not supported: database_copy 'to' cannot be '{env_name}' in extension 'our-postgres'."
    assert msg in console_message


def test_validate_database_copy_multi_postgres_success():
    config = {
        "application": "test-app",
        "environments": {"dev": {}, "test": {}, "prod": {}},
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "dev", "to": "test"}],
            },
            "our-other-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "dev", "to": "test"}, {"from": "prod", "to": "dev"}],
            },
        },
    }

    ConfigValidator().validate_database_copy_section(config)

    # Should get here fine if the config is valid.


def test_validate_database_copy_multi_postgres_failures(capsys):
    config = {
        "application": "test-app",
        "environments": {"dev": {}, "test": {}, "prod": {}},
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "devvv", "to": "test"}],
            },
            "our-other-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "test", "to": "test"}, {"from": "dev", "to": "prod"}],
            },
        },
    }

    with pytest.raises(SystemExit):
        ConfigValidator().validate_database_copy_section(config)

    console_message = capsys.readouterr().err

    assert (
        f"database_copy 'from' parameter must be a valid environment (dev, test, prod) but was 'devvv' in extension 'our-postgres'."
        in console_message
    )
    assert (
        f"database_copy 'to' and 'from' cannot be the same environment in extension 'our-other-postgres'."
        in console_message
    )
    assert (
        f"Copying to a prod environment is not supported: database_copy 'to' cannot be 'prod' in extension 'our-other-postgres'."
        in console_message
    )


def test_validate_database_copy_fails_if_cross_account_with_no_from_account(capsys):
    config = {
        "application": "test-app",
        "environments": {
            "dev": {"accounts": {"deploy": {"id": "1122334455"}}},
            "prod": {"accounts": {"deploy": {"id": "9999999999"}}},
        },
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "prod", "to": "dev"}],
            }
        },
    }

    with pytest.raises(SystemExit):
        ConfigValidator().validate_database_copy_section(config)

    console_message = capsys.readouterr().err

    msg = f"Environments 'prod' and 'dev' are in different AWS accounts. The 'from_account' parameter must be present."
    assert msg in console_message


def test_validate_database_copy_fails_if_cross_account_with_no_to_account(capsys):
    config = {
        "application": "test-app",
        "environments": {
            "dev": {"accounts": {"deploy": {"id": "1122334455"}}},
            "prod": {"accounts": {"deploy": {"id": "9999999999"}}},
        },
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "prod", "to": "dev", "from_account": "9999999999"}],
            }
        },
    }

    with pytest.raises(SystemExit):
        ConfigValidator().validate_database_copy_section(config)

    console_message = capsys.readouterr().err

    msg = f"Environments 'prod' and 'dev' are in different AWS accounts. The 'to_account' parameter must be present."
    assert msg in console_message


def test_validate_database_copy_fails_if_cross_account_with_incorrect_account_ids(capsys):
    config = {
        "application": "test-app",
        "environments": {
            "dev": {"accounts": {"deploy": {"id": "1122334455"}}},
            "prod": {"accounts": {"deploy": {"id": "9999999999"}}},
        },
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [
                    {
                        "from": "prod",
                        "to": "dev",
                        "from_account": "000000000",
                        "to_account": "1111111111",
                    }
                ],
            }
        },
    }

    with pytest.raises(SystemExit):
        ConfigValidator().validate_database_copy_section(config)

    console_message = capsys.readouterr().err

    msg = f"Incorrect value for 'from_account' for environment 'prod'"
    assert msg in console_message


def test_validate_platform_config_fails_if_database_copy_config_is_invalid(
    capsys,
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

    with pytest.raises(SystemExit):
        ConfigValidator().validate_database_copy_section(config)

    message = capsys.readouterr().err

    assert (
        f"database_copy 'to' and 'from' cannot be the same environment in extension 'our-postgres'."
        in message
    )


def test_validate_platform_config_catches_environment_pipeline_errors(platform_env_config, capsys):
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

    with pytest.raises(SystemExit):
        ConfigValidator().validate_environment_pipelines(platform_env_config)

    message = capsys.readouterr().err

    assert "The following pipelines are misconfigured:" in message
    assert f"  'main' - these environments are not in the 'non-prod' account: dev" in message
    assert f"  'prod' - these environments are not in the 'prod' account: dev, staging" in message


@pytest.mark.parametrize(
    "account, envs, exp_bad_envs",
    [
        ("account-does-not-exist", ["dev"], ["dev"]),
        ("prod-acc", ["dev", "staging", "prod"], ["dev", "staging"]),
        ("non-prod-acc", ["dev", "prod"], ["prod"]),
    ],
)
def test_validate_platform_config_fails_if_pipeline_account_does_not_match_environment_accounts_with_single_pipeline(
    platform_env_config, account, envs, exp_bad_envs, capsys
):
    config = ConfigProvider.apply_environment_defaults(platform_env_config)
    config["environment_pipelines"] = {
        "main": {
            "account": account,
            "slack_channel": "/codebuild/notification_channel",
            "trigger_on_push": True,
            "environments": {env: {} for env in envs},
        }
    }

    with pytest.raises(SystemExit):
        ConfigValidator().validate_environment_pipelines(config)

    message = capsys.readouterr().err

    assert "The following pipelines are misconfigured:" in message
    assert (
        f"  'main' - these environments are not in the '{account}' account: {', '.join(exp_bad_envs)}"
        in message
    )


@pytest.mark.parametrize("pipeline_to_trigger", ("", "non-existent-pipeline"))
def test_validate_platform_config_fails_if_pipeline_to_trigger_not_valid(
    platform_env_config, pipeline_to_trigger, capsys
):
    platform_env_config["environment_pipelines"] = {
        "main": {
            "account": "1122334455",
            "slack_channel": "/codebuild/notification_channel",
            "trigger_on_push": True,
            "environments": {"dev": {}},
            "pipeline_to_trigger": pipeline_to_trigger,
        },
        "prod-main": {
            "account": "9999999999",
            "slack_channel": "/codebuild/notification_channel",
            "trigger_on_push": True,
            "environments": {"prod": {}},
        },
    }

    with pytest.raises(SystemExit):
        ConfigValidator().validate_environment_pipelines_triggers(platform_env_config)

    message = capsys.readouterr().err

    assert "The following pipelines are misconfigured:" in message
    assert (
        f"  'main' - '{pipeline_to_trigger}' is not a valid target pipeline to trigger" in message
    )


def test_validate_platform_config_fails_with_multiple_errors_if_pipeline_to_trigger_is_invalid(
    valid_platform_config, capsys
):
    valid_platform_config["environment_pipelines"]["main"]["pipeline_to_trigger"] = ""
    valid_platform_config["environment_pipelines"]["test"][
        "pipeline_to_trigger"
    ] = "non-existent-pipeline"

    with pytest.raises(SystemExit):
        ConfigValidator().validate_environment_pipelines_triggers(valid_platform_config)

    message = capsys.readouterr().err

    assert "The following pipelines are misconfigured:" in message
    assert f"  'main' - '' is not a valid target pipeline to trigger" in message
    assert (
        f"  'test' - 'non-existent-pipeline' is not a valid target pipeline to trigger" in message
    )


def test_validate_platform_config_fails_if_pipeline_to_trigger_is_triggering_itself(
    valid_platform_config, capsys
):
    valid_platform_config["environment_pipelines"]["main"]["pipeline_to_trigger"] = "main"

    with pytest.raises(SystemExit):
        ConfigValidator().validate_environment_pipelines_triggers(valid_platform_config)

    message = capsys.readouterr().err

    assert "The following pipelines are misconfigured:" in message
    assert f"  'main' - pipelines cannot trigger themselves" in message


@pytest.mark.parametrize(
    "config, expected_response",
    [
        (
            # No engine defined in either env
            {
                "extensions": {
                    "connors-redis": {
                        "type": "redis",
                        "environments": {"*": {"plan": "tiny"}, "prod": {"plan": "largish"}},
                    }
                },
            },
            "",
        ),
        (
            # Valid engine version defined in *
            {
                "extensions": {
                    "connors-redis": {
                        "type": "redis",
                        "environments": {
                            "*": {"engine": "7.1", "plan": "tiny"},
                            "prod": {"plan": "tiny"},
                        },
                    }
                },
            },
            "",
        ),
        (
            # Invalid engine defined in prod environment
            {
                "extensions": {
                    "connors-redis": {
                        "type": "redis",
                        "environments": {
                            "*": {"plan": "tiny"},
                            "prod": {"engine": "invalid", "plan": "tiny"},
                        },
                    }
                },
            },
            "redis version for environment prod is not in the list of supported redis versions: ['7.1']. Provided Version: invalid",
        ),
    ],
)
def test_validate_extension_supported_versions(config, expected_response, capsys):

    mock_redis_provider = MagicMock()
    mock_redis_provider.get_supported_redis_versions.return_value = ["7.1"]

    ConfigValidator()._validate_extension_supported_versions(
        config=config,
        extension_type="redis",
        version_key="engine",
        get_supported_versions=mock_redis_provider.get_supported_redis_versions,
    )

    captured = capsys.readouterr()

    assert expected_response in captured.out
    assert captured.err == ""


def test_two_codebase_pipelines_cannot_manage_the_same_environments(fakefs, capsys):
    config = {
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
                    {"name": "main", "branch": "main", "environments": [{"name": "dev"}]},
                    {"name": "other", "branch": "main", "environments": [{"name": "dev"}]},
                ],
            }
        ],
    }
    with pytest.raises(SystemExit):
        ConfigValidator().validate_codebase_pipelines(config)

    exp = (
        f"Error: The {PLATFORM_CONFIG_FILE} file is invalid, each environment can"
        " only be listed in a single pipeline per codebase"
    )
    assert exp in capsys.readouterr().err
