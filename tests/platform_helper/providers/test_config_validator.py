from unittest.mock import MagicMock

import pytest

from dbt_platform_helper.domain.config_validator import ConfigValidator


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
    capfd, database_copy_section, expected_parameters
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

    console_message = capfd.readouterr().err

    for param in expected_parameters:
        msg = f"database_copy '{param}' parameter must be a valid environment (dev, test, prod) but was 'hotfix' in extension 'our-postgres'."
        assert msg in console_message


def test_validate_database_copy_fails_if_from_and_to_are_the_same(capfd):
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

    console_message = capfd.readouterr().err

    msg = (
        f"database_copy 'to' and 'from' cannot be the same environment in extension 'our-postgres'."
    )
    assert msg in console_message


@pytest.mark.parametrize(
    "env_name",
    ["prod", "prod-env", "env-that-is-prod", "thing-prod-thing"],
)
def test_validate_database_copy_section_fails_if_the_to_environment_is_prod(capfd, env_name):
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

    console_message = capfd.readouterr().err

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


def test_validate_database_copy_multi_postgres_failures(capfd):
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

    console_message = capfd.readouterr().err

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


def test_validate_database_copy_fails_if_cross_account_with_no_from_account(capfd):
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

    console_message = capfd.readouterr().err

    msg = f"Environments 'prod' and 'dev' are in different AWS accounts. The 'from_account' parameter must be present."
    assert msg in console_message


def test_validate_database_copy_fails_if_cross_account_with_no_to_account(capfd):
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

    console_message = capfd.readouterr().err

    msg = f"Environments 'prod' and 'dev' are in different AWS accounts. The 'to_account' parameter must be present."
    assert msg in console_message


def test_validate_database_copy_fails_if_cross_account_with_incorrect_account_ids(capfd):
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

    console_message = capfd.readouterr().err

    msg = f"Incorrect value for 'from_account' for environment 'prod'"
    assert msg in console_message


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
        (
            # Invalid extensions type defined in prod environment
            {"extensions": {"connors-redis": {"type": "redis", "environments": True}}},
            "Error: redis extension definition is invalid type, expected dictionary",
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
