import os
import re
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import call

import pytest
import yaml

from dbt_platform_helper.constants import CODEBASE_PIPELINES_KEY
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.platform_config_schema import CURRENT_SCHEMA_VERSION
from dbt_platform_helper.providers.yaml_file import DuplicateKeysException
from dbt_platform_helper.providers.yaml_file import InvalidYamlException
from tests.platform_helper.conftest import FIXTURES_DIR


class TestLoadAndValidate:
    def test_comprehensive_platform_config_validates_successfully(self, valid_platform_config):
        mock_file_provider = Mock(spec=FileProvider)
        mock_file_provider.load.return_value = valid_platform_config
        config_provider = ConfigProvider(ConfigValidator(), mock_file_provider)

        config_provider.load_and_validate_platform_config()
        # No assertions as this will raise an error if there is one.

    def test_load_and_validate_exits_if_load_fails_with_duplicate_keys_error(self, capsys):
        mock_file_provider = Mock(spec=FileProvider)
        mock_file_provider.load.side_effect = DuplicateKeysException("repeated-key")
        config_provider = ConfigProvider(ConfigValidator(), mock_file_provider)

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        assert "Duplicate keys found in your config file: repeated-key" in capsys.readouterr().err

    def test_load_and_validate_exits_with_invalid_yaml(self, capsys):
        """Test that, given the an invalid yaml file, load_and_validate_config
        aborts and prints an error."""
        mock_file_provider = Mock(spec=FileProvider)
        mock_file_provider.load.side_effect = InvalidYamlException("platform-config.yml")
        config_provider = ConfigProvider(ConfigValidator(), mock_file_provider)

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        assert f"{PLATFORM_CONFIG_FILE} is not valid YAML" in capsys.readouterr().err

    def test_load_and_validate_platform_config_fails_with_missing_config_file(self, capsys):
        if Path(PLATFORM_CONFIG_FILE).exists():
            os.remove(Path(PLATFORM_CONFIG_FILE))

        with pytest.raises(SystemExit):
            ConfigProvider(ConfigValidator()).load_and_validate_platform_config()

        assert (
            f"`{PLATFORM_CONFIG_FILE}` is missing. Please check it exists and you are in the root directory of your deployment project."
            in capsys.readouterr().err
        )

    @pytest.mark.parametrize(
        "account, envs",
        [
            ("non-prod-acc", ["dev", "staging"]),
            ("prod-acc", ["prod"]),
        ],
    )
    def test_load_and_validate_with_valid_environment_pipeline_accounts(
        self, platform_env_config, account, envs
    ):
        platform_env_config["environment_pipelines"] = {
            "main": {
                "account": account,
                "slack_channel": "/codebuild/notification_channel",
                "trigger_on_push": True,
                "environments": {env: {} for env in envs},
            }
        }

        mock_file_provider = Mock(spec=FileProvider)
        mock_file_provider.load.return_value = platform_env_config
        config_provider = ConfigProvider(ConfigValidator(), mock_file_provider)

        # Should not error if config is sound.
        config_provider.load_and_validate_platform_config()

    @pytest.mark.parametrize(
        "yaml_file",
        [
            "pipeline/platform-config.yml",
            "pipeline/platform-config-with-public-repo.yml",
            "pipeline/platform-config-for-terraform.yml",
        ],
    )
    def test_load_and_validate_config_valid_file(self, yaml_file):
        """Test that, given the path to a valid yaml file,
        load_and_validate_config returns the loaded yaml unmodified."""

        config_provider = ConfigProvider(ConfigValidator())

        path = FIXTURES_DIR / yaml_file
        validated = config_provider.load_and_validate_platform_config(path=path)

        with open(path, "r") as fd:
            conf = yaml.safe_load(fd)

        assert validated == {"schema_version": CURRENT_SCHEMA_VERSION, **conf}

    def test_load_and_validate_config_migrations_run_and_print_messages(self):
        mock_migrator = Mock()
        mock_migrator.messages.return_value = [
            "Migration warning one",
            "Migration warning two",
        ]
        mock_io = Mock()
        config_provider = ConfigProvider(ConfigValidator(), io=mock_io, migrator=mock_migrator)
        path = FIXTURES_DIR / "pipeline/platform-config.yml"
        config_provider.load_and_validate_platform_config(path=path)

        mock_migrator.migrate.assert_called_once()
        mock_migrator.messages.assert_called_once()
        assert mock_io.warn.call_args_list == [
            call("Migration warning one"),
            call("Migration warning two"),
        ]

    def test_load_unvalidated_config_file_returns_a_dict_given_valid_yaml(self, fakefs):
        fakefs.create_file(
            Path(PLATFORM_CONFIG_FILE),
            contents="""
        test:
            some_key: some_value
        """,
        )
        config_provider = ConfigProvider()
        config = config_provider.load_unvalidated_config_file()

        assert config == {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "test": {"some_key": "some_value"},
        }

    def test_load_unvalidated_config_file_returns_minimal_dict_given_invalid_yaml(self, fakefs):
        fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents="{")
        config_provider = ConfigProvider()
        config = config_provider.load_unvalidated_config_file()

        assert config == {"schema_version": CURRENT_SCHEMA_VERSION}


class TestDataMigrationValidation:
    def test_validate_data_migration_fails_if_neither_import_nor_import_sources_present(self):
        """Edge cases for this are all covered in unit tests of
        validate_database_copy_section elsewhere in this file."""
        config = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "application": "test-app",
            "extensions": {
                "test-s3-bucket": {
                    "type": "s3",
                    "environments": {
                        "dev": {
                            "bucket_name": "placeholder-to-pass-schema-validation",
                            "data_migration": {},
                        }
                    },
                }
            },
        }

        mock_file_provider = Mock(spec=FileProvider)
        mock_file_provider.load.return_value = config
        mock_io = Mock()

        config_provider = ConfigProvider(ConfigValidator(), mock_file_provider, mock_io)

        config_provider.load_and_validate_platform_config()

        mock_io.abort_with_error.assert_called_with(
            """Config validation has failed.\n'import_sources' property in 'test-s3-bucket.environments.dev.data_migration' is missing."""
        )

    def test_validate_data_migration_fails_if_both_import_and_import_sources_present(self):
        """Edge cases for this are all covered in unit tests of
        validate_database_copy_section elsewhere in this file."""
        config = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "application": "test-app",
            "extensions": {
                "test-s3-bucket": {
                    "type": "s3",
                    "environments": {
                        "dev": {
                            "bucket_name": "placeholder-to-pass-schema-validation",
                            "data_migration": {
                                "import": {
                                    "source_bucket_arn": "arn:aws:s3:::end-to-end-tests-s3-data-migration-source",
                                    "source_kms_key_arn": "arn:aws:kms:eu-west-2:763451185160:key/0602bd28-253c-4ba8-88f5-cb34cb2ffb54",
                                    "worker_role_arn": "arn:aws:iam::763451185160:role/end-to-end-tests-s3-data-migration-worker",
                                },
                                "import_sources": [
                                    {
                                        "source_bucket_arn": "arn:aws:s3:::end-to-end-tests-s3-data-migration-source",
                                        "source_kms_key_arn": "arn:aws:kms:eu-west-2:763451185160:key/0602bd28-253c-4ba8-88f5-cb34cb2ffb54",
                                        "worker_role_arn": "arn:aws:iam::763451185160:role/end-to-end-tests-s3-data-migration-worker",
                                    }
                                ],
                            },
                        }
                    },
                }
            },
        }

        config_provider = ConfigProvider(ConfigValidator())
        config_provider.config = config
        mock_io = Mock()
        config_provider.io = mock_io

        config_provider._validate_platform_config()

        mock_io.abort_with_error.assert_called_with(
            """Config validation has failed.\nError in 'test-s3-bucket.environments.dev.data_migration': only the 'import_sources' property is required - 'import' is deprecated."""
        )


class TestGetEnrichedConfig:
    def test_get_enriched_config_returns_config_with_environment_defaults_applied(self):
        mock_file_provider = Mock(spec=FileProvider)
        mock_file_provider.load.return_value = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "application": "test-app",
            "environments": {
                "*": {
                    "vpc": "vpc3",
                    "accounts": {
                        "deploy": {"name": "non-prod-acc", "id": "1122334455"},
                        "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
                    },
                },
                "test": {},
            },
        }

        expected_enriched_config = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "application": "test-app",
            "environments": {
                "test": {
                    "vpc": "vpc3",
                    "accounts": {
                        "deploy": {"name": "non-prod-acc", "id": "1122334455"},
                        "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
                    },
                }
            },
        }

        mock_config_validator = Mock()

        result = ConfigProvider(mock_config_validator, mock_file_provider).get_enriched_config()

        assert result == expected_enriched_config

    @pytest.mark.parametrize(
        "mock_environment_config, expected_vpc_for_test_environment",
        [
            ({"test": {}}, None),
            ({"test": {"vpc": "vpc1"}}, "vpc1"),
            ({"*": {"vpc": "vpc2"}, "test": None}, "vpc2"),
            ({"*": {"vpc": "vpc3"}, "test": {"vpc": "vpc4"}}, "vpc4"),
        ],
    )
    def test_get_enriched_config_correctly_resolves_vpc_for_environment_with_environment_defaults_applied(
        self, mock_environment_config, expected_vpc_for_test_environment
    ):
        mock_file_provider = Mock(spec=FileProvider)
        mock_file_provider.load.return_value = {
            "application": "test-app",
            "environments": mock_environment_config,
        }

        result = ConfigProvider(Mock(), mock_file_provider).get_enriched_config()

        assert (
            result.get("environments").get("test").get("vpc") == expected_vpc_for_test_environment
        )


class TestVersionValidations:
    def test_validation_fails_if_invalid_default_version_keys_present(
        self, capsys, valid_platform_config
    ):
        valid_platform_config["default_versions"] = {"something-invalid": "1.2.3"}

        mock_file_provider = Mock(spec=FileProvider)
        mock_file_provider.load.return_value = valid_platform_config
        config_provider = ConfigProvider(ConfigValidator(), mock_file_provider)

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        assert "Wrong key 'something-invalid'" in capsys.readouterr().err

    @pytest.mark.parametrize(
        "invalid_key",
        (
            "",
            "invalid-key",
            "terraform-platform-modules",  # terraform-platform-modules is not valid in the pipeline overrides.
        ),
    )
    def test_validation_fails_if_invalid_pipeline_version_override_keys_present(
        self, invalid_key, valid_platform_config, capsys
    ):
        valid_platform_config["environment_pipelines"]["test"]["versions"][invalid_key] = "1.2.3"

        mock_file_provider = Mock(spec=FileProvider)
        mock_file_provider.load.return_value = valid_platform_config

        config_provider = ConfigProvider(ConfigValidator(), mock_file_provider)

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        assert f"Wrong key '{invalid_key}'" in capsys.readouterr().err


class TestApplyEnvironmentDefaults:
    def test_apply_defaults(self):

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
                "one": {"a": "aaa", "b": {"c": "ccc"}},
                "two": {"a": "aaa", "b": {"c": "ccc"}},
                "three": {"a": "override_aaa", "b": {"d": "ddd"}, "c": "ccc"},
            },
        }

    def test_apply_defaults_with_no_defaults(self):
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
                "one": {},
                "two": {},
                "three": {"a": "aaa"},
            },
        }


class TestCodebasePipelineValidations:
    def test_codebase_pipeline_run_groups_validate(self):
        platform_config = {
            "application": "test-app",
            "codebase_pipelines": {
                "application": {
                    "repository": "organisation/repository",
                    "services": [
                        {"run_group_1": ["web"]},
                        {"run_group_2": ["api", "celery-beat"]},
                    ],
                    "pipelines": [
                        {"name": "main", "branch": "main", "environments": [{"name": "dev"}]}
                    ],
                }
            },
        }
        mock_file_provider = Mock(spec=FileProvider)
        mock_file_provider.load.return_value = platform_config

        config = ConfigProvider(
            ConfigValidator(), mock_file_provider
        ).load_and_validate_platform_config()

        assert config[CODEBASE_PIPELINES_KEY]["application"]["services"] == [
            {"run_group_1": ["web"]},
            {"run_group_2": ["api", "celery-beat"]},
        ]

    @pytest.mark.parametrize("channel", [1, [], {}, True])
    def test_codebase_slack_channel_fails_if_not_a_string(self, channel, capsys):
        config = {
            "application": "test-app",
            "codebase_pipelines": {
                "application": {
                    "name": "application",
                    "slack_channel": channel,
                    "repository": "organisation/repository",
                    "services": [],
                    "pipelines": [],
                }
            },
        }
        mock_file_provider = Mock(spec=FileProvider)
        mock_file_provider.load.return_value = config

        with pytest.raises(SystemExit):
            ConfigProvider(
                ConfigValidator(), mock_file_provider
            ).load_and_validate_platform_config()

        error = capsys.readouterr().err

        exp = r".*Key 'slack_channel' error:.*'?%s'? should be instance of 'str'.*" % re.escape(
            str(channel)
        )
        assert re.match(exp, error, re.DOTALL)

    @pytest.mark.parametrize("requires_image", [1, "brian", [], {}])
    def test_codebase_requires_image_build_fails_if_not_a_bool(self, capsys, requires_image):
        config = {
            "application": "test-app",
            "codebase_pipelines": {
                "application": {
                    "name": "application",
                    "requires_image_build": requires_image,
                    "slack_channel": "channel",
                    "repository": "organisation/repository",
                    "services": [],
                    "pipelines": [],
                }
            },
        }
        mock_file_provider = Mock(spec=FileProvider)
        mock_file_provider.load.return_value = config

        with pytest.raises(SystemExit):
            ConfigProvider(
                ConfigValidator(), mock_file_provider
            ).load_and_validate_platform_config()
        error = capsys.readouterr().err

        exp = (
            r".*Key 'requires_image_build' error:.*'?%s'? should be instance of 'bool'.*"
            % re.escape(str(requires_image))
        )
        assert re.match(exp, error, re.DOTALL)
