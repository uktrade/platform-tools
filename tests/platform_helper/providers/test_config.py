import os
import re
from pathlib import Path
from unittest.mock import create_autospec

import pytest
import yaml
from freezegun import freeze_time
from schema import SchemaError

from dbt_platform_helper.constants import CODEBASE_PIPELINES_KEY
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_CONFIG_SCHEMA_VERSION
from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.version import InstalledVersionProvider
from dbt_platform_helper.providers.yaml_file import DuplicateKeysException
from dbt_platform_helper.providers.yaml_file import InvalidYamlException
from dbt_platform_helper.providers.yaml_file import YamlFileProvider
from tests.platform_helper.conftest import FIXTURES_DIR


def expected_schema_pre_validation_header(
    installed_platform_helper_version: str,
    installed_schema_version: int,
    config_platform_helper_version: str,
    config_schema_version: int,
):
    return f"""Installed version: platform-helper: {installed_platform_helper_version} (schema version: {installed_schema_version})
'platform-config.yml' version: platform-helper: {config_platform_helper_version} (schema version: {config_schema_version})"""


class ConfigProviderMocks:
    def __init__(
        self,
        platform_config_content=None,
        use_mock_config_validator=False,
        use_mock_io=False,
        schema_version=PLATFORM_CONFIG_SCHEMA_VERSION,
    ):
        if platform_config_content is None:
            platform_config_content = {}
        self.config_validator = (
            create_autospec(ConfigValidator, spec_set=True)
            if use_mock_config_validator
            else ConfigValidator()
        )
        self.file_provider = create_autospec(YamlFileProvider, spec_set=True)
        self.file_provider.load.return_value = platform_config_content
        self.io = (
            create_autospec(spec=ClickIOProvider, spec_set=True)
            if use_mock_io
            else ClickIOProvider()
        )
        self.installed_version_provider = create_autospec(
            spec=InstalledVersionProvider, spec_set=True
        )
        self.installed_version_provider.get_semantic_version.return_value = SemanticVersion(
            14, 0, 0
        )
        self.schema_version = schema_version

    def params(self):
        return {
            "config_validator": self.config_validator,
            "file_provider": self.file_provider,
            "io": self.io,
            "schema_version_for_installed_platform_helper": self.schema_version,
            "installed_version_provider": self.installed_version_provider,
        }


class TestLoadAndValidate:
    def test_comprehensive_platform_config_validates_successfully(self, valid_platform_config):
        config_provider = ConfigProvider(**ConfigProviderMocks(valid_platform_config).params())

        config_provider.load_and_validate_platform_config()
        # No assertions as this will raise an error if there is one.

    def test_load_and_validate_exits_if_load_fails_with_duplicate_keys_error(self, capsys):
        config_provider_mocks = ConfigProviderMocks({})
        config_provider_mocks.file_provider.load.side_effect = DuplicateKeysException(
            "repeated-key"
        )
        config_provider = ConfigProvider(**config_provider_mocks.params())

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        assert "Duplicate keys found in your config file: repeated-key" in capsys.readouterr().err

    def test_load_and_validate_exits_if_schema_version_is_missing_and_platform_tools_is_v_13(
        self, capsys
    ):
        """
        This scenario could occur if the configured platform-helper version is
        13.x.x.

        i.e. prior to the schema_version being introduced, but we do provide
        automated migrations for v13.x.x
        """
        config = {
            "application": "test_application",
            "default_versions": {"platform-helper": "13.3.0"},
        }
        config_provider_mocks = ConfigProviderMocks(config, schema_version=3)
        config_provider = ConfigProvider(**config_provider_mocks.params())

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        expected_header = expected_schema_pre_validation_header("14.0.0", 3, "13.3.0", "N/A")
        expected_error = f"""Error: {expected_header}\n\nPlease upgrade your platform-config.yml to be compatible with 14.0.0 by running: 'platform-helper config migrate'."""
        actual_error = capsys.readouterr().err

        assert actual_error.strip() == expected_error

    @pytest.mark.parametrize("config_platform_helper_version", ["12.0.0", "11.4.0", "12.6.0"])
    def test_load_and_validate_exits_if_platform_tools_prior_to_13(
        self, config_platform_helper_version, capsys
    ):
        """
        This scenario could occur if the configured platform-helper version is
        before 13.x.x.

        i.e. prior to the schema_version being introduced and too early to use
        automated migrations for the upgrade
        """
        config = {
            "application": "test_application",
            "default_versions": {"platform-helper": config_platform_helper_version},
        }

        config_provider_mocks = ConfigProviderMocks(config, schema_version=3)
        config_provider = ConfigProvider(**config_provider_mocks.params())

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        expected_header = expected_schema_pre_validation_header(
            "14.0.0", 3, config_platform_helper_version, "N/A"
        )

        expected_error = f"""Error: {expected_header}

Please ensure that you have already upgraded to platform-helper 13, following the instructions in https://platform.readme.trade.gov.uk/reference/upgrading-platform-helper/.

Then upgrade platform-helper to version 14.0.0 and run 'platform-helper config migrate' to upgrade the configuration to the current schema version."""

        actual_error = capsys.readouterr().err

        assert actual_error.strip() == expected_error

    def test_load_and_validate_exits_if_no_schema_version_or_platform_helper_default(self, capsys):
        """This scenario could occur if your platform-helper version is very old
        and does not even have a platform-helper default version."""
        config = {
            "application": "test_application",
        }
        config_provider_mocks = ConfigProviderMocks(config, schema_version=3)
        config_provider = ConfigProvider(**config_provider_mocks.params())

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        expected_header = expected_schema_pre_validation_header("14.0.0", 3, "N/A", "N/A")
        expected_error = f"""Error: {expected_header}

Please ensure that you have already upgraded to platform-helper 13, following the instructions in https://platform.readme.trade.gov.uk/reference/upgrading-platform-helper/.

Then upgrade platform-helper to version 14.0.0 and run 'platform-helper config migrate' to upgrade the configuration to the current schema version."""
        actual_error = capsys.readouterr().err

        assert actual_error.strip() == expected_error

    def test_load_and_validate_continues_to_validation_if_schema_version_missing_and_platform_tools_after_13(
        self, capsys
    ):
        """
        This scenario could occur if the configured platform-helper version is
        14.0.0 or later.

        It is invalid configuration at this point as schema_version is mandatory
        in 14.0.0 and above, so we let schema validation handle it.
        """
        config = {
            "application": "test_application",
            "default_versions": {"platform-helper": "14.0.0"},
        }
        config_provider_mocks = ConfigProviderMocks(config, schema_version=3)
        config_provider = ConfigProvider(**config_provider_mocks.params())

        with pytest.raises(SystemExit) as exc:
            config_provider.load_and_validate_platform_config()

        assert exc.value.code == 1
        assert f"Missing key: 'schema_version'" in capsys.readouterr().err

    def test_load_and_validate_exits_if_schema_version_is_lower_than_the_current_schema_version(
        self, capsys
    ):
        """
        This scenario could occur if you update platform-helper to a newer
        version that has changed the schema version.

        i.e. your platform-config.yml declares schema_version: 3 and the latest platform-helper
        requires schema_version: 5
        """
        config = {
            "schema_version": 4,
            "application": "test_application",
            "default_versions": {"platform-helper": "16.0.0"},
        }

        config_provider_mocks = ConfigProviderMocks(config, schema_version=7)
        config_provider = ConfigProvider(**config_provider_mocks.params())
        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        expected_header = expected_schema_pre_validation_header("14.0.0", 7, "16.0.0", 4)

        assert (
            f"""{expected_header}

Please upgrade your platform-config.yml by running 'platform-helper config migrate'."""
            in capsys.readouterr().err
        )

    def test_load_and_validate_exits_if_schema_version_is_after_the_current_schema_version(
        self, capsys
    ):
        """
        This scenario could occur if your platform-config.yml declares
        schema_version: 6 for example but you are using an older version of
        platform-helper.

        i.e. your platform-config.yml declares schema_version: 6 and the platform-helper you have installed
        requires schema_version: 5
        """
        config = {
            "schema_version": 4,
            "application": "test_application",
            "default_versions": {"platform-helper": "14.2.0"},
        }

        config_provider_mocks = ConfigProviderMocks(config, schema_version=2)
        config_provider = ConfigProvider(**config_provider_mocks.params())

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        expected_header = expected_schema_pre_validation_header("14.0.0", 2, "14.2.0", 4)
        expected_error = f"Error: {expected_header}\n\nPlease update your platform-helper to a version that supports schema_version: 4."
        actual_error = capsys.readouterr().err.strip()

        assert actual_error == expected_error

    def test_load_and_validate_exits_with_invalid_yaml(self, capsys):
        """Test that, given the an invalid yaml file, load_and_validate_config
        aborts and prints an error."""

        config_provider_mocks = ConfigProviderMocks({})
        config_provider_mocks.file_provider.load.side_effect = InvalidYamlException(
            "platform-config.yml"
        )
        config_provider = ConfigProvider(**config_provider_mocks.params())

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        assert f"{PLATFORM_CONFIG_FILE} is not valid YAML" in capsys.readouterr().err

    def test_load_and_validate_platform_config_fails_with_missing_config_file(self, capsys):
        if Path(PLATFORM_CONFIG_FILE).exists():
            os.remove(Path(PLATFORM_CONFIG_FILE))
        config_provider_mocks = ConfigProviderMocks()
        config_provider = ConfigProvider(
            installed_version_provider=config_provider_mocks.installed_version_provider
        )

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

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

        config_provider_mocks = ConfigProviderMocks(platform_env_config)
        config_provider = ConfigProvider(**config_provider_mocks.params())
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

        config_provider_mocks = ConfigProviderMocks()
        config_provider = ConfigProvider(
            installed_version_provider=config_provider_mocks.installed_version_provider
        )

        path = FIXTURES_DIR / yaml_file
        validated = config_provider.load_and_validate_platform_config(path=path)

        with open(path, "r") as fd:
            conf = yaml.safe_load(fd)

        assert validated == {"schema_version": PLATFORM_CONFIG_SCHEMA_VERSION, **conf}

    def test_load_unvalidated_config_file_returns_a_dict_given_valid_yaml(self, fakefs):
        fakefs.create_file(
            Path(PLATFORM_CONFIG_FILE),
            contents=f"""
        test:
            some_key: some_value
        """,
        )
        config_provider_mocks = ConfigProviderMocks()
        config_provider = ConfigProvider(
            installed_version_provider=config_provider_mocks.installed_version_provider
        )
        config = config_provider.load_unvalidated_config_file()

        assert config == {
            "test": {"some_key": "some_value"},
        }

    def test_load_unvalidated_config_file_returns_minimal_dict_given_invalid_yaml(self, fakefs):
        fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents="{")
        config_provider_mocks = ConfigProviderMocks()
        config_provider = ConfigProvider(
            installed_version_provider=config_provider_mocks.installed_version_provider
        )

        config = config_provider.load_unvalidated_config_file()

        assert config == {}


class TestDataMigrationValidation:
    def test_validate_data_migration_fails_if_neither_import_nor_import_sources_present(self):
        """Edge cases for this are all covered in unit tests of
        validate_database_copy_section elsewhere in this file."""
        config = {
            "schema_version": PLATFORM_CONFIG_SCHEMA_VERSION,
            "default_versions": {"platform-helper": "14.0.0"},
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

        config_provider_mocks = ConfigProviderMocks(config, use_mock_io=True)
        config_provider = ConfigProvider(**config_provider_mocks.params())

        config_provider.load_and_validate_platform_config()

        config_provider.io.abort_with_error.assert_called_with(
            """Config validation has failed.\n'import_sources' property in 'test-s3-bucket.environments.dev.data_migration' is missing."""
        )

    def test_validate_data_migration_fails_if_both_import_and_import_sources_present(self):
        """Edge cases for this are all covered in unit tests of
        validate_database_copy_section elsewhere in this file."""
        config = {
            "schema_version": PLATFORM_CONFIG_SCHEMA_VERSION,
            "default_versions": {"platform-helper": "14.0.0"},
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

        config_provider_mocks = ConfigProviderMocks(config, use_mock_io=True)
        config_provider = ConfigProvider(**config_provider_mocks.params())
        config_provider.config = config

        config_provider._validate_platform_config()

        config_provider.io.abort_with_error.assert_called_with(
            """Config validation has failed.\nError in 'test-s3-bucket.environments.dev.data_migration': only the 'import_sources' property is required - 'import' is deprecated."""
        )

    @pytest.mark.parametrize("schema_version", [0, 9000000])
    def test_validate_data_migration_fails_if_schema_version_wrong(self, schema_version):
        config = {
            "schema_version": schema_version,
            "default_versions": {"platform-helper": "14.0.0"},
            "application": "test-app",
        }

        config_provider_mocks = ConfigProviderMocks(config, use_mock_io=True)
        config_provider = ConfigProvider(**config_provider_mocks.params())
        config_provider.config = config

        with pytest.raises(SchemaError) as exc:
            config_provider._validate_platform_config()

        assert (
            str(exc.value)
            == f"Key 'schema_version' error:\n{PLATFORM_CONFIG_SCHEMA_VERSION} does not match {schema_version}"
        )

    def test_validate_data_migration_fails_if_schema_version_missing(self):
        config = {
            "application": "test-app",
            "default_versions": {"platform-helper": "14.0.0"},
        }

        config_provider_mocks = ConfigProviderMocks(config, use_mock_io=True)
        config_provider = ConfigProvider(**config_provider_mocks.params())
        config_provider.config = config

        with pytest.raises(SchemaError) as exc:
            config_provider._validate_platform_config()

        assert str(exc.value) == f"Missing key: 'schema_version'"

    def test_validate_data_migration_fails_if_service_deployment_mode_not_supported(self):
        config = {
            "application": "test-app",
            "schema_version": 1,
            "default_versions": {"platform-helper": "14.0.0"},
            "environments": {"dev": {"service-deployment-mode": "something we dont want"}},
        }

        config_provider_mocks = ConfigProviderMocks(config, use_mock_io=True)
        config_provider = ConfigProvider(**config_provider_mocks.params())
        config_provider.config = config

        with pytest.raises(SchemaError) as exc:
            config_provider._validate_platform_config()

        assert "'copilot' does not match 'something we dont want'" in str(exc.value)
        assert "'dual-deploy-copilot-traffic' does not match 'something we dont want'" in str(
            exc.value
        )
        assert "'dual-deploy-platform-traffic' does not match 'something we dont want'" in str(
            exc.value
        )
        assert "'platform' does not match 'something we dont want'" in str(exc.value)

    def test_validate_data_migration_fails_if_bucket_is_static(self):
        config = {
            "schema_version": PLATFORM_CONFIG_SCHEMA_VERSION,
            "default_versions": {"platform-helper": "14.0.0"},
            "application": "test-app",
            "extensions": {
                "test-s3-bucket": {
                    "type": "s3",
                    "serve_static_content": True,
                    "environments": {
                        "dev": {
                            "bucket_name": "placeholder-to-pass-schema-validation",
                            "data_migration": {
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

        config_provider_mocks = ConfigProviderMocks(config, use_mock_io=True)
        config_provider = ConfigProvider(**config_provider_mocks.params())

        config_provider.load_and_validate_platform_config()

        config_provider.io.abort_with_error.assert_called_with(
            "Config validation has failed.\nData migration is not supported for static S3 buckets to avoid the risk of unintentionally exposing private data. However, you can copy data on an ad hoc basis using AWS CLI commands such as 'aws s3 sync' or 'aws s3 cp'."
        )


class TestGetEnrichedConfig:
    def test_get_enriched_config_returns_config_with_environment_defaults_applied(self):
        config = {
            "schema_version": PLATFORM_CONFIG_SCHEMA_VERSION,
            "default_versions": {"platform-helper": "14.0.0"},
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
            "schema_version": PLATFORM_CONFIG_SCHEMA_VERSION,
            "default_versions": {"platform-helper": "14.0.0"},
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

        config_provider_mocks = ConfigProviderMocks(config, use_mock_config_validator=True)
        config_provider = ConfigProvider(**config_provider_mocks.params())
        result = config_provider.get_enriched_config()

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
        config = {
            "schema_version": PLATFORM_CONFIG_SCHEMA_VERSION,
            "default_versions": {"platform-helper": "14.0.0"},
            "application": "test-app",
            "environments": mock_environment_config,
        }

        config_provider_mocks = ConfigProviderMocks(config, use_mock_config_validator=True)
        config_provider = ConfigProvider(**config_provider_mocks.params())
        result = config_provider.get_enriched_config()

        assert (
            result.get("environments").get("test").get("vpc") == expected_vpc_for_test_environment
        )


class TestVersionValidations:
    def test_validation_fails_if_invalid_default_version_keys_present(
        self, capsys, valid_platform_config
    ):
        valid_platform_config["default_versions"] = {
            "platform-helper": "14.0.0",
            "something-invalid": "1.2.3",
        }

        mock_file_provider = create_autospec(YamlFileProvider, spec_set=True)
        mock_file_provider.load.return_value = valid_platform_config
        config_provider = ConfigProvider(ConfigValidator(), mock_file_provider)

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        assert "Wrong key 'something-invalid'" in capsys.readouterr().err

    def test_validation_fails_if_default_versions_missing(self, capsys, valid_platform_config):
        del valid_platform_config["default_versions"]

        mock_file_provider = create_autospec(YamlFileProvider, spec_set=True)
        mock_file_provider.load.return_value = valid_platform_config
        config_provider = ConfigProvider(ConfigValidator(), mock_file_provider)

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        assert "Missing key: 'default_versions'" in capsys.readouterr().err

    def test_validation_fails_if_default_version_platform_helper_missing(
        self, capsys, valid_platform_config
    ):
        valid_platform_config["default_versions"] = {}

        mock_file_provider = create_autospec(YamlFileProvider, spec_set=True)
        mock_file_provider.load.return_value = valid_platform_config
        config_provider = ConfigProvider(ConfigValidator(), mock_file_provider)

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        assert "Missing key: 'platform-helper'" in capsys.readouterr().err

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

        config_provider = ConfigProvider(**ConfigProviderMocks(valid_platform_config).params())

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
            "schema_version": PLATFORM_CONFIG_SCHEMA_VERSION,
            "default_versions": {"platform-helper": "14.0.0"},
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

        config_provider_mocks = ConfigProviderMocks(platform_config)
        config_provider = ConfigProvider(**config_provider_mocks.params())
        config = config_provider.load_and_validate_platform_config()

        assert config[CODEBASE_PIPELINES_KEY]["application"]["services"] == [
            {"run_group_1": ["web"]},
            {"run_group_2": ["api", "celery-beat"]},
        ]

    @pytest.mark.parametrize("channel", [1, [], {}, True])
    def test_codebase_slack_channel_fails_if_not_a_string(self, channel, capsys):
        config = {
            "schema_version": PLATFORM_CONFIG_SCHEMA_VERSION,
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

        config_provider_mocks = ConfigProviderMocks(config)
        config_provider = ConfigProvider(**config_provider_mocks.params())

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()

        error = capsys.readouterr().err

        exp = r".*Key 'slack_channel' error:.*'?%s'? should be instance of 'str'.*" % re.escape(
            str(channel)
        )
        assert re.match(exp, error, re.DOTALL)

    @pytest.mark.parametrize("requires_image", [1, "brian", [], {}])
    def test_codebase_requires_image_build_fails_if_not_a_bool(self, capsys, requires_image):
        config = {
            "schema_version": PLATFORM_CONFIG_SCHEMA_VERSION,
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

        config_provider_mocks = ConfigProviderMocks(config)
        config_provider = ConfigProvider(**config_provider_mocks.params())

        with pytest.raises(SystemExit):
            config_provider.load_and_validate_platform_config()
        error = capsys.readouterr().err

        exp = (
            r".*Key 'requires_image_build' error:.*'?%s'? should be instance of 'bool'.*"
            % re.escape(str(requires_image))
        )
        assert re.match(exp, error, re.DOTALL)


class TestWritePlatformConfig:
    @freeze_time("2025-01-16 13:00:00")
    def test_write_platform_config(self):
        config_provider_mocks = ConfigProviderMocks({})
        config_provider = ConfigProvider(**config_provider_mocks.params())

        config_provider.write_platform_config({"application": "test-app"})

        expected_comment = f"# Generated by platform-helper 14.0.0 / 2025-01-16 13:00:00.\n\n"

        config_provider_mocks.file_provider.write.assert_called_once_with(
            PLATFORM_CONFIG_FILE, {"application": "test-app"}, expected_comment
        )
