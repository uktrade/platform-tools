from unittest.mock import MagicMock

import pytest

from dbt_platform_helper.domain.config_validator import ConfigValidator
from dbt_platform_helper.domain.config_validator import ConfigValidatorError
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
        ([{"from": "test", "to": "dev"}, {"from": "dev", "to": "hotfix"}], ["to"]),
        ([{"from": "hotfix", "to": "test"}, {"from": "dev", "to": "test"}], ["from"]),
    ],
)
def test_validate_database_copy_section_failure_cases(database_copy_section, expected_parameters):
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

    with pytest.raises(ConfigValidatorError) as exception:
        ConfigValidator().validate_database_copy_section(config)

    console_message = str(exception)

    for param in expected_parameters:
        msg = f"database_copy '{param}' parameter must be a valid environment (dev, test, prod) but was 'hotfix' in extension 'our-postgres'."
        assert msg in console_message


@pytest.mark.parametrize(
    "env_name",
    ["prod", "prod-env", "env-that-is-prod", "thing-prod-thing"],
)
def test_validate_database_copy_section_fails_if_the_to_environment_is_prod(env_name):
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

    with pytest.raises(ConfigValidatorError) as exception:
        ConfigValidator().validate_database_copy_section(config)

    console_message = str(exception.value)

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


def test_validate_database_copy_multi_postgres_failures():
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

    with pytest.raises(ConfigValidatorError) as exception:
        ConfigValidator().validate_database_copy_section(config)

    console_message = str(exception.value)

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


def test_validate_database_copy_fails_if_cross_account_with_no_from_account():
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

    with pytest.raises(ConfigValidatorError) as exception:
        ConfigValidator().validate_database_copy_section(config)

    console_message = str(exception.value)

    msg = f"Environments 'prod' and 'dev' are in different AWS accounts. The 'from_account' parameter must be present."
    assert msg in console_message


def test_validate_database_copy_fails_if_cross_account_with_no_to_account():
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

    with pytest.raises(ConfigValidatorError) as exception:
        ConfigValidator().validate_database_copy_section(config)

    console_message = str(exception.value)

    msg = f"Environments 'prod' and 'dev' are in different AWS accounts. The 'to_account' parameter must be present."
    assert msg in console_message


def test_validate_database_copy_fails_if_cross_account_with_incorrect_account_ids():
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

    with pytest.raises(ConfigValidatorError) as exception:
        ConfigValidator().validate_database_copy_section(config)

    console_message = str(exception.value)

    msg = f"Incorrect value for 'from_account' for environment 'prod'"
    assert msg in console_message


def test_validate_platform_config_fails_if_database_copy_to_and_from_are_the_same():
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

    with pytest.raises(ConfigValidatorError) as exception:
        ConfigValidator().validate_database_copy_section(config)

    console_message = str(exception.value)

    assert (
        f"database_copy 'to' and 'from' cannot be the same environment in extension 'our-postgres'."
        in console_message
    )


def test_validate_platform_config_fails_if_environments_are_not_in_the_pipeline_account(
    platform_env_config,
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

    with pytest.raises(ConfigValidatorError) as exception:
        ConfigValidator().validate_environment_pipelines(platform_env_config)

    console_message = str(exception.value)

    assert "The following pipelines are misconfigured:" in console_message
    assert (
        f"  'main' - these environments are not in the 'non-prod' account: dev" in console_message
    )
    assert (
        f"  'prod' - these environments are not in the 'prod' account: dev, staging"
        in console_message
    )


@pytest.mark.parametrize(
    "account, envs, exp_bad_envs",
    [
        ("account-does-not-exist", ["dev"], ["dev"]),
        ("prod-acc", ["dev", "staging", "prod"], ["dev", "staging"]),
        ("non-prod-acc", ["dev", "prod"], ["prod"]),
    ],
)
def test_validate_platform_config_fails_if_pipeline_account_does_not_match_environment_accounts_with_single_pipeline(
    platform_env_config, account, envs, exp_bad_envs
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

    with pytest.raises(ConfigValidatorError) as exception:
        ConfigValidator().validate_environment_pipelines(config)

    console_message = str(exception.value)

    assert "The following pipelines are misconfigured:" in console_message
    assert (
        f"  'main' - these environments are not in the '{account}' account: {', '.join(exp_bad_envs)}"
        in console_message
    )


@pytest.mark.parametrize("pipeline_to_trigger", ("", "non-existent-pipeline"))
def test_validate_platform_config_fails_if_pipeline_to_trigger_not_valid(
    platform_env_config, pipeline_to_trigger
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

    with pytest.raises(ConfigValidatorError) as exception:
        ConfigValidator().validate_environment_pipelines_triggers(platform_env_config)

    console_message = str(exception.value)

    assert "The following pipelines are misconfigured:" in console_message
    assert (
        f"  'main' - '{pipeline_to_trigger}' is not a valid target pipeline to trigger"
        in console_message
    )


def test_validate_platform_config_fails_with_multiple_errors_if_pipeline_to_trigger_is_invalid(
    valid_platform_config,
):
    valid_platform_config["environment_pipelines"]["main"]["pipeline_to_trigger"] = ""
    valid_platform_config["environment_pipelines"]["test"][
        "pipeline_to_trigger"
    ] = "non-existent-pipeline"

    with pytest.raises(ConfigValidatorError) as exception:
        ConfigValidator().validate_environment_pipelines_triggers(valid_platform_config)

    console_message = str(exception.value)

    assert "The following pipelines are misconfigured:" in console_message
    assert f"  'main' - '' is not a valid target pipeline to trigger" in console_message
    assert (
        f"  'test' - 'non-existent-pipeline' is not a valid target pipeline to trigger"
        in console_message
    )


def test_validate_platform_config_fails_if_pipeline_to_trigger_is_triggering_itself(
    valid_platform_config,
):
    valid_platform_config["environment_pipelines"]["main"]["pipeline_to_trigger"] = "main"

    with pytest.raises(ConfigValidatorError) as exception:
        ConfigValidator().validate_environment_pipelines_triggers(valid_platform_config)

    console_message = str(exception.value)

    assert "The following pipelines are misconfigured:" in console_message
    assert f"  'main' - pipelines cannot trigger themselves" in console_message


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
            "redis version for environment prod is not in the list of supported redis versions: ['6.2', '7.0', '7.1']. Provided Version: invalid",
        ),
        (
            # Invalid extensions type defined in prod environment
            {"extensions": {"connors-redis": {"type": "redis", "environments": True}}},
            "Error: redis extension definition is invalid type, expected dictionary",
        ),
    ],
)
def test_validate_extension_supported_versions(config, expected_response, capsys):
    mock_redis_provider = MagicMock()

    ConfigValidator()._validate_extension_supported_versions(
        config=config,
        aws_provider=mock_redis_provider,
        extension_type="redis",
        version_key="engine",
    )

    captured = capsys.readouterr()

    assert expected_response in captured.out
    assert captured.err == ""
