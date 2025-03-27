import os
import re
from pathlib import Path
from pathlib import PosixPath
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml
from botocore.exceptions import ClientError
from freezegun import freeze_time

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.domain.copilot import Copilot
from dbt_platform_helper.domain.copilot_environment import CopilotTemplating
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.kms import KMSProvider
from dbt_platform_helper.utils.application import Environment
from tests.platform_helper.conftest import FIXTURES_DIR

REDIS_STORAGE_CONTENTS = {
    "redis": {"type": "redis", "environments": {"default": {"engine": "6.2", "plan": "small"}}}
}

POSTGRES_STORAGE_CONTENTS = {
    "rds": {"type": "postgres", "version": 14.4, "environments": {"default": {"plan": "small-ha"}}}
}

OPENSEARCH_STORAGE_CONTENTS = {
    "opensearch": {
        "type": "opensearch",
        "environments": {"default": {"plan": "small", "engine": "2.3"}},
    }
}

S3_STORAGE_CONTENTS = {
    "s3": {
        "type": "s3",
        "readonly": True,
        "services": ["web"],
        "environments": {
            "development": {"bucket_name": "my-bucket-dev"},
            "production": {"bucket_name": "my-bucket-prod"},
        },
    }
}

WEB_SERVICE_CONTENTS = {"name": "web", "type": "Load Balanced Web Service"}

ALB_CONTENTS = {
    "alb": {
        "type": "alb",
        "environments": {
            "default": {
                "cdn_domains_list": {"test.domain.uktrade.digital": "domain.uktrade.digital"},
                "additional_address_list": ["another.domain"],
            },
            "development": None,
            # "empty" "to" "verify" "it" "can" "handle" "an" "environment" "with" "no" "config"
        },
    }
}

PROMETHEUS_WRITE_POLICY_CONTENTS = """
prometheus:
  type: prometheus-write-policy
  services:
    - "web"
  role_arn: arn:nonprod:fake:fake:fake:fake
  environments:
    production:
      role_arn: role_arn: arn:prod:fake:fake:fake:fake
"""

EXTENSION_CONFIG_FILENAME = "extensions.yml"


class CopilotMocks:
    def __init__(self, **kwargs):
        self.parameter_provider = kwargs.get("parameter_provider", Mock())
        self.file_provider = kwargs.get("file_provider", Mock())
        self.copilot_templating = kwargs.get("copilot_templating", Mock(spec=CopilotTemplating))
        self.kms_provider = kwargs.get("kms_provider", Mock(spec=KMSProvider))
        self.session = kwargs.get("session", Mock())
        self.config_provider = kwargs.get("config_provider", Mock(spec=ConfigProvider))
        self.io = kwargs.get("io", Mock(spec=ClickIOProvider))
        # Use fakefs patch instead of mocking YamlFileProvider

    def params(self):
        return {
            "parameter_provider": self.parameter_provider,
            "file_provider": self.file_provider,
            "copilot_templating": self.copilot_templating,
            "kms_provider": self.kms_provider,
            "session": self.session,
            "config_provider": self.config_provider,
            "io": self.io,
        }


class TestMakeAddonsCommand:
    @pytest.mark.parametrize(
        "kms_key_exists, kms_key_arn",
        (
            (True, "arn-for-kms-alias"),
            (False, "kms-key-not-found"),
        ),
    )
    @freeze_time("2023-08-22 16:00:00")
    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch(
        "dbt_platform_helper.domain.copilot.Copilot._get_log_destination_arn",
        new=Mock(
            return_value='{"prod": "arn:cwl_log_destination_prod", "dev": "arn:dev_cwl_log_destination"}'
        ),
    )
    @patch(
        "dbt_platform_helper.utils.application.get_profile_name_from_account_id",
        new=Mock(return_value="foo"),
    )
    @patch("dbt_platform_helper.domain.copilot.load_application", autospec=True)
    def test_s3_kms_arn_is_rendered_in_template(
        self,
        mock_application,
        fakefs,
        kms_key_exists,
        kms_key_arn,
    ):
        dev_session = MagicMock(name="dev-session-mock")
        dev_session.profile_name = "foo"
        prod_session = MagicMock(name="prod-session-mock")
        prod_session.profile_name = "bar"
        client = MagicMock(name="client-mock")
        dev_session.client.return_value = client
        prod_session.client.return_value = client

        dev = Environment(
            name="development",
            account_id="000000000000",
            sessions={"000000000000": dev_session},
        )
        prod = Environment(
            name="production",
            account_id="111111111111",
            sessions={"111111111111": prod_session},
        )
        mock_application.return_value.environments = {
            "development": dev,
            "production": prod,
        }

        create_test_manifests(S3_STORAGE_CONTENTS, fakefs)

        mocks = CopilotMocks()

        mocks.session.side_effect = [dev_session, prod_session]

        config = {
            "application": "test-app",
            "extensions": S3_STORAGE_CONTENTS,
            "environments": {"development": {}, "production": {}},
        }
        mocks.config_provider.apply_environment_defaults = lambda config: config
        mocks.config_provider.load_and_validate_platform_config.return_value = config
        mocks.file_provider = FileProvider  # Allow the use of fakefs

        if kms_key_exists:
            mocks.kms_provider.return_value.describe_key.return_value = {
                "KeyMetadata": {"Arn": kms_key_arn}
            }
        else:
            error = {"Error": {"Code": "NotFoundException"}}
            mocks.kms_provider.return_value.describe_key.side_effect = ClientError(
                error, "NotFoundException"
            )

        Copilot(**mocks.params()).make_addons()

        s3_addon = yaml.safe_load(Path(f"/copilot/web/addons/s3.yml").read_text())

        assert (
            s3_addon["Mappings"]["s3EnvironmentConfigMap"]["development"]["KmsKeyArn"]
            == kms_key_arn
        )

        assert (
            s3_addon["Mappings"]["s3EnvironmentConfigMap"]["production"]["KmsKeyArn"] == kms_key_arn
        )

        dev_session.client.assert_called_once_with("kms")
        prod_session.client.assert_called_with("kms")
        assert mocks.kms_provider.return_value.describe_key.call_count == 2

        assert "alias/test-app-production-my-bucket-prod-key" in str(
            mocks.kms_provider.return_value.describe_key.call_args_list
        )

        assert "alias/test-app-development-my-bucket-dev-key" in str(
            mocks.kms_provider.return_value.describe_key.call_args_list
        )
        assert dev_session != prod_session

    @pytest.mark.parametrize(
        "addon_file, expected_service_addons",
        [
            (
                "s3_addons.yml",
                [
                    "appconfig-ipfilter.yml",
                    "subscription-filter.yml",
                    "prometheus.yml",
                    "my-s3-bucket.yml",
                    "my-s3-bucket-with-an-object.yml",
                    "my-s3-bucket-bucket-access.yml",
                ],
            ),
            (
                "opensearch_addons.yml",
                ["appconfig-ipfilter.yml", "prometheus.yml", "subscription-filter.yml"],
            ),
            (
                "rds_addons.yml",
                ["appconfig-ipfilter.yml", "prometheus.yml", "subscription-filter.yml"],
            ),
            (
                "redis_addons.yml",
                ["appconfig-ipfilter.yml", "prometheus.yml", "subscription-filter.yml"],
            ),
            (
                "monitoring_addons.yml",
                ["appconfig-ipfilter.yml", "prometheus.yml", "subscription-filter.yml"],
            ),
            (
                "prometheus_policy_addons.yml",
                [
                    "appconfig-ipfilter.yml",
                    "subscription-filter.yml",
                    "prometheus.yml",
                    "prometheus-test.yml",
                ],
            ),
        ],
    )
    @freeze_time("2023-08-22 16:00:00")
    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch(
        "dbt_platform_helper.domain.copilot.Copilot._get_log_destination_arn",
        new=Mock(
            return_value='{"prod": "arn:cwl_log_destination_prod", "dev": "arn:dev_cwl_log_destination"}'
        ),
    )
    @patch("dbt_platform_helper.domain.copilot.load_application", autospec=True)
    def test_terraform_compatible_make_addons_success(
        self,
        mock_application,
        fakefs,
        addon_file,
        expected_service_addons,
    ):
        """Test that make_addons generates the expected directories and file
        contents."""
        # Arrange
        dev_session = MagicMock(name="dev-session-mock")
        dev_session.profile_name = "foo"
        prod_session = MagicMock(name="prod-session-mock")
        prod_session.profile_name = "bar"
        client = MagicMock(name="client-mock")
        dev_session.client.return_value = client
        prod_session.client.return_value = client

        dev = Environment(
            name="development",
            account_id="000000000000",
            sessions={"000000000000": dev_session},
        )
        prod = Environment(
            name="production",
            account_id="111111111111",
            sessions={"111111111111": prod_session},
        )
        mock_application.return_value.environments = {
            "development": dev,
            "production": prod,
        }

        mocks = CopilotMocks()

        config = {
            "application": "test-app",
            "extensions": S3_STORAGE_CONTENTS,
            "environments": {"development": {}, "production": {}},
        }
        mocks.config_provider.apply_environment_defaults = lambda config: config
        mocks.config_provider.load_and_validate_platform_config.return_value = config
        mocks.file_provider = FileProvider  # Allow the use of fakefs
        mocks.kms_provider.return_value.describe_key.return_value = {
            "KeyMetadata": {"Arn": "kms-key-not-found"}
        }

        addons_dir = FIXTURES_DIR / "make_addons"
        fakefs.add_real_directory(
            addons_dir / "config/copilot", read_only=False, target_path="copilot"
        )
        fakefs.add_real_file(
            addons_dir / addon_file, read_only=False, target_path=PLATFORM_CONFIG_FILE
        )
        fakefs.add_real_directory(Path(addons_dir, "expected"), target_path="expected")

        # Act
        Copilot(**mocks.params()).make_addons()

        assert any(
            ">>> Generating Terraform compatible addons CloudFormation" in str(arg)
            for arg in mocks.io.info.call_args_list
        )

        expected_service_files = [
            Path("web/addons", filename) for filename in expected_service_addons
        ]

        for f in expected_service_files:
            if "s3" in str(f):
                # Use the terraform-* fixtures for s3
                parts = (
                    "expected",
                    *f.parts[:-1],
                    f"terraform-{f.name}",
                )
                expected_file = Path(*parts)
            else:
                expected_file = Path("expected", f)

            expected = yaml.safe_load(expected_file.read_text())
            actual = yaml.safe_load(Path("copilot", f).read_text())

            assert sorted(expected) == sorted(
                actual
            ), f"The file {f} did not have the expected content"

            assert actual == expected

        assert not Path("./copilot/environments/addons/").exists()

        env_override_file = Path("./copilot/environments/overrides/cfn.patches.yml")

        expected_env_overrides_file = Path(
            "expected/environments/overrides/cfn.patches.yml"
        ).read_text()
        actual_env_overrides_file = Path(
            "copilot/environments/overrides/cfn.patches.yml"
        ).read_text()

        assert actual_env_overrides_file == expected_env_overrides_file

        all_expected_files = expected_service_files + [env_override_file]

        expected_svc_overrides_file = Path("expected/web/overrides/cfn.patches.yml").read_text()
        actual_svc_overrides_file = Path("copilot/web/overrides/cfn.patches.yml").read_text()
        assert actual_svc_overrides_file == expected_svc_overrides_file

        copilot_dir = Path("copilot")
        actual_files = [
            Path(d, f).relative_to(copilot_dir)
            for d, _, files in os.walk(copilot_dir)
            for f in files
        ]

        assert (
            len(actual_files) == len(all_expected_files) + 5
        ), "The actual filecount should be expected files plus 3 initial manifest.yml and 1 override files"

    @freeze_time("2023-08-22 16:00:00")
    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch(
        "dbt_platform_helper.domain.copilot.Copilot._get_log_destination_arn",
        new=Mock(
            return_value='{"prod": "arn:cwl_log_destination_prod", "dev": "arn:dev_cwl_log_destination"}'
        ),
    )
    def test_make_addons_removes_old_addons_files(
        self,
        fakefs,
    ):
        """Tests that old addons files are cleaned up before generating new
        ones."""

        # Arrange

        mocks = CopilotMocks()

        config = {
            "application": "test-app",
            "extensions": S3_STORAGE_CONTENTS,
            "environments": {"development": {}, "production": {}},
        }
        mocks.config_provider.apply_environment_defaults = lambda config: config
        mocks.config_provider.load_and_validate_platform_config.return_value = config
        mocks.file_provider = FileProvider  # Allow the use of fakefs

        addons_dir = FIXTURES_DIR / "make_addons"
        fakefs.add_real_directory(
            addons_dir / "config/copilot", read_only=False, target_path="copilot"
        )
        fakefs.add_real_file(
            addons_dir / "redis_addons.yml",
            read_only=False,
            target_path=PLATFORM_CONFIG_FILE,
        )
        fakefs.add_real_directory(Path(addons_dir, "expected"), target_path="expected")

        # Add some legacy addon files:
        old_addon_files = [
            "environments/addons/my-s3-bucket.yml",
            "environments/addons/my-s3-bucket-with-an-object.yml",
            "environments/addons/my-opensearch.yml",
            "environments/addons/my-rds-db.yml",
            "web/addons/my-s3-bucket.yml",
            "web/addons/my-s3-bucket-with-an-object.yml",
            "web/addons/my-s3-bucket-bucket-access.yml",
        ]

        for f in old_addon_files:
            fakefs.create_file(Path("copilot", f), contents="Does not matter")

        # Act
        Copilot(**mocks.params()).make_addons()

        # Assert
        expected_service_files = [
            Path("web/addons", f) for f in ["appconfig-ipfilter.yml", "subscription-filter.yml"]
        ]
        all_expected_files = expected_service_files

        for f in all_expected_files:
            expected_file = Path(
                "expected",
                f if not f.name == "vpc.yml" else "environments/addons/vpc-default.yml",
            )
            expected = yaml.safe_load(expected_file.read_text())
            actual = yaml.safe_load(Path("copilot", f).read_text())
            assert sorted(actual) == sorted(
                expected
            ), f"The file {f} did not have the expected content"

        for f in old_addon_files:
            path = Path("copilot", f)
            assert not path.exists(), f"{path} should not exist"

    def test_exit_if_no_local_copilot_services(self, fakefs):
        fakefs.create_file(PLATFORM_CONFIG_FILE)
        fakefs.create_file("copilot/environments/development/manifest.yml")
        mocks = CopilotMocks()
        mocks.io.abort_with_error.side_effect = SystemExit(1)

        with pytest.raises(SystemExit):
            Copilot(**mocks.params()).make_addons()

        assert any(
            "No services found in ./copilot/; exiting" in str(arg)
            for arg in mocks.io.abort_with_error.call_args_list
        )

    def test_exit_with_error_if_invalid_services(self, fakefs):
        fakefs.create_file(
            PLATFORM_CONFIG_FILE,
            contents=yaml.dump(
                {
                    "extensions": {
                        "invalid-entry": {
                            "type": "s3-policy",
                            "services": ["does-not-exist", "also-does-not-exist"],
                            "environments": {"default": {"bucket_name": "test-bucket"}},
                        }
                    }
                }
            ),
        )

        fakefs.create_file("copilot/environments/development/manifest.yml")
        fakefs.create_file("copilot/web/manifest.yml", contents=yaml.dump(WEB_SERVICE_CONTENTS))
        mocks = CopilotMocks()
        mocks.io.abort_with_error.side_effect = SystemExit(1)

        with pytest.raises(SystemExit):
            Copilot(**mocks.params()).make_addons()

        assert any(
            "Services listed in invalid-entry.services do not exist in ./copilot/" in str(arg)
            for arg in mocks.io.error.call_args_list
        )

        assert any(
            "Configuration has errors. Exiting." in str(arg)
            for arg in mocks.io.abort_with_error.call_args_list
        )

    def test_exit_with_error_if_addons_yml_validation_fails(self, fakefs):
        fakefs.create_file(
            PLATFORM_CONFIG_FILE,
            contents=yaml.dump(
                {
                    "extensions": {
                        "example-invalid-file": {
                            "type": "s3",
                            "environments": {
                                "default": {"bucket_name": "test-bucket", "no_such_key": "bad-key"}
                            },
                        }
                    }
                }
            ),
        )

        fakefs.create_file("copilot/environments/development/manifest.yml")
        fakefs.create_file("copilot/web/manifest.yml", contents=yaml.dump(WEB_SERVICE_CONTENTS))

        mocks = CopilotMocks()
        mocks.io.abort_with_error.side_effect = SystemExit(1)

        with pytest.raises(SystemExit):
            Copilot(**mocks.params()).make_addons()

        assert re.match(
            r"(?s).*example-invalid-file.*environments.*default.*Wrong key 'no_such_key'",
            mocks.io.error.call_args_list[-1][0][0],
        )

    def test_exit_with_multiple_errors_if_invalid_environments(self, fakefs):
        fakefs.create_file(
            PLATFORM_CONFIG_FILE,
            contents=yaml.dump(
                {
                    "extensions": {
                        "invalid-environment": {
                            "type": "s3-policy",
                            "services": ["does-not-exist", "also-does-not-exist"],
                            "environments": {
                                "doesnotexist": {"bucket_name": "test-bucket"},
                                "alsodoesnotexist": {"bucket_name": "test-bucket-2"},
                            },
                        },
                        "invalid-environment-2": {
                            "type": "s3",
                            "environments": {
                                "andanotherdoesnotexist": {"bucket_name": "test-bucket"}
                            },
                        },
                    }
                }
            ),
        )

        fakefs.create_file("copilot/environments/development/manifest.yml")
        fakefs.create_file("copilot/web/manifest.yml", contents=yaml.dump(WEB_SERVICE_CONTENTS))

        mocks = CopilotMocks()
        mocks.io.abort_with_error.side_effect = SystemExit(1)

        with pytest.raises(SystemExit):
            Copilot(**mocks.params()).make_addons()

        assert any(
            "Environment keys listed in invalid-environment do not match those defined in ./copilot/environments"
            in str(arg)
            for arg in mocks.io.error.call_args_list
        )
        assert any(
            "Missing environments: alsodoesnotexist, doesnotexist" in str(arg)
            for arg in mocks.io.error.call_args_list
        )
        assert any(
            "Environment keys listed in invalid-environment do not match those defined in ./copilot/environments"
            in str(arg)
            for arg in mocks.io.error.call_args_list
        )
        assert any(
            "Environment keys listed in invalid-environment-2 do not match those defined in ./copilot/environments"
            in str(arg)
            for arg in mocks.io.error.call_args_list
        )
        assert any(
            "Missing environments: andanotherdoesnotexist" in str(arg)
            for arg in mocks.io.error.call_args_list
        )
        assert any(
            "Services listed in invalid-environment.services do not exist in ./copilot/" in str(arg)
            for arg in mocks.io.error.call_args_list
        )

    def test_exit_with_multiple_errors(self, fakefs):
        fakefs.create_file(
            PLATFORM_CONFIG_FILE,
            contents=yaml.dump(
                {
                    "extensions": {
                        "my-s3-bucket-1": {
                            "type": "s3",
                            "environments": {
                                "dev": {
                                    "bucket_name": "sthree-one..TWO-s3alias"  # "Many" "naming" "errors"
                                }
                            },
                        },
                        "my-s3-bucket-2": {
                            "type": "s3",
                            "environments": {
                                "dev": {
                                    "bucket_name": "charles",
                                    "deletion_policy": "ThisIsInvalid",  # "Should" "be" "a" "valid" "policy" "name".
                                }
                            },
                        },
                    }
                }
            ),
        )

        fakefs.create_file("copilot/environments/development/manifest.yml")
        fakefs.create_file("copilot/web/manifest.yml", contents=yaml.dump(WEB_SERVICE_CONTENTS))

        mocks = CopilotMocks()
        mocks.io.abort_with_error.side_effect = SystemExit(1)

        with pytest.raises(SystemExit):
            Copilot(**mocks.params()).make_addons()

        assert any(
            f"Errors found in {PLATFORM_CONFIG_FILE}:" in str(arg)
            for arg in mocks.io.error.call_args_list
        )
        assert any(
            "'Delete' does not match 'ThisIsInvalid'" in str(arg)
            for arg in mocks.io.error.call_args_list
        )
        assert any(
            "Names cannot be prefixed 'sthree-'" in str(arg)
            for arg in mocks.io.error.call_args_list
        )
        assert any(
            "Names cannot be suffixed '-s3alias'" in str(arg)
            for arg in mocks.io.error.call_args_list
        )
        assert any(
            "Names cannot contain two adjacent periods" in str(arg)
            for arg in mocks.io.error.call_args_list
        )
        assert any(
            "Names can only contain the characters 0-9, a-z, '.' and '-'." in str(arg)
            for arg in mocks.io.error.call_args_list
        )

    def test_exit_if_services_key_invalid(self, fakefs):
        """
        The services key can be set to a list of services, or '__all__' which
        denotes that it should be applied to all services.

        Any other string value results in an error.
        """

        fakefs.create_file(
            PLATFORM_CONFIG_FILE,
            contents=yaml.dump(
                {
                    "extensions": {
                        "invalid-entry": {
                            "type": "s3-policy",
                            "services": "this-is-not-valid",
                            "environments": {"default": {"bucket-name": "test-bucket"}},
                        }
                    }
                }
            ),
        )

        fakefs.create_file("copilot/environments/development/manifest.yml")

        fakefs.create_file("copilot/web/manifest.yml", contents=yaml.dump(WEB_SERVICE_CONTENTS))

        mocks = CopilotMocks()
        mocks.io.abort_with_error.side_effect = SystemExit(1)
        with pytest.raises(SystemExit):
            Copilot(**mocks.params()).make_addons()

        mocks.io.abort_with_error.assert_called_with(
            "Invalid platform-config.yml provided, see above warnings"
        )
        assert any("Key 'services' error:" in str(arg) for arg in mocks.io.error.call_args_list)
        assert any(
            "'__all__' does not match 'this-is-not-valid'" in str(arg)
            for arg in mocks.io.error.call_args_list
        )
        assert any(
            "'this-is-not-valid' should be instance of 'list'" in str(arg)
            for arg in mocks.io.error.call_args_list
        )

    def test_exit_if_no_local_copilot_environments(self):
        mocks = CopilotMocks()
        mocks.io.abort_with_error.side_effect = SystemExit(1)

        with pytest.raises(SystemExit):
            Copilot(**mocks.params()).make_addons()

        assert (
            "No environments found in ./copilot/environments; exiting" in str(arg)
            for arg in mocks.io.error.call_args_list
        )

    @pytest.mark.parametrize(
        "addon_config, addon_type, secret_name",
        [
            (REDIS_STORAGE_CONTENTS, "redis", "REDIS"),
            (POSTGRES_STORAGE_CONTENTS, "postgres", "RDS"),
        ],
    )
    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    def test_addon_instructions_with_postgres_addon_types(
        self,
        addon_config,
        addon_type,
        secret_name,
        fakefs,
        capsys,
    ):
        create_test_manifests(addon_config, fakefs)
        mocks = CopilotMocks()
        mock_config = {
            "application": "test-app",
            "extensions": addon_config,
            "environments": {"development": {}, "production": {}},
        }

        mocks.config_provider.config_file_check.return_value = True
        mocks.config_provider.load_and_validate_platform_config.return_value = mock_config
        mocks.config_provider.apply_environment_defaults = lambda config: config
        mocks.parameter_provider.get_ssm_parameter_by_name.return_value = {
            "Value": '{"prod": "arn:cwl_log_destination_prod", "dev": "arn:dev_cwl_log_destination"}'
        }

        Copilot(**mocks.params()).make_addons()

        assert any(
            ">>> Generating Terraform compatible addons CloudFormation" in str(arg)
            for arg in mocks.io.info.call_args_list
        )

        # Assert on multiple ways that db credentials could be exposed in output
        if addon_type == "redis":
            captured = capsys.readouterr()
            assert "DATABASE_CREDENTIALS" not in captured.out
            assert all(
                "DATABASE_CREDENTIALS" not in str(arg) for arg in mocks.io.info.call_args_list
            )

        if addon_type == "redis":
            assert (
                "REDIS_ENDPOINT: /copilot/${COPILOT_APPLICATION_NAME}/${COPILOT_ENVIRONMENT_NAME}/secrets/REDIS"
                in mocks.io.info.call_args_list[-1][0][0]
            )
        else:
            assert (
                "secretsmanager: /copilot/${COPILOT_APPLICATION_NAME}/${COPILOT_ENVIRONMENT_NAME}/secrets/RDS"
                in mocks.io.info.call_args_list[-1][0][0]
            )

    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch(
        "dbt_platform_helper.domain.copilot.Copilot._get_log_destination_arn",
        new=Mock(
            return_value='{"prod": "arn:cwl_log_destination_prod", "dev": "arn:dev_cwl_log_destination"}'
        ),
    )
    @patch("dbt_platform_helper.domain.copilot.load_application", autospec=True)
    def test_appconfig_ip_filter_policy_is_applied_to_each_service_by_default(
        self,
        mock_application,
        fakefs,
    ):

        mock_config = {
            "application": "test-app",
            "environments": {"development": {}},
            "extensions": {"foo": {"type": "s3", "environments": {"development": {}}}},
        }

        fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(mock_config))

        fakefs.create_file(
            "./copilot/environments/development/manifest.yml",
        )

        for service in ["test-1", "test-2"]:
            fakefs.create_file(
                f"copilot/{service}/manifest.yml", contents=yaml.dump(WEB_SERVICE_CONTENTS)
            )

        mocks = CopilotMocks()

        mocks.file_provider = FileProvider

        mocks.config_provider.load_and_validate_platform_config.return_value = mock_config
        mocks.config_provider.apply_environment_defaults = lambda conf: conf

        mocks.copilot_templating = Mock(spec=CopilotTemplating)
        mocks.copilot_templating.generate_cross_account_s3_policies.return_value = "TestData"

        mock_kms_instance = Mock()
        mock_kms_instance.describe_key.return_value = {"KeyMetadata": {"Arn": "arn-for-kms-alias"}}
        mock_kms = Mock()
        mock_kms.return_value = mock_kms_instance
        mocks.kms_provider = mock_kms

        Copilot(**mocks.params()).make_addons()

        assert Path(f"copilot/test-1/addons/appconfig-ipfilter.yml").exists()
        assert Path(f"copilot/test-1/addons/subscription-filter.yml").exists()
        assert Path(f"copilot/test-2/addons/appconfig-ipfilter.yml").exists()
        assert Path(f"copilot/test-2/addons/subscription-filter.yml").exists()

    @freeze_time("2023-08-22 16:00:00")
    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch(
        "dbt_platform_helper.domain.copilot.Copilot._get_log_destination_arn",
        new=Mock(
            return_value='{"prod": "arn:cwl_log_destination_prod", "dev": "arn:dev_cwl_log_destination"}'
        ),
    )
    @patch(
        "dbt_platform_helper.utils.application.get_profile_name_from_account_id",
        new=Mock(return_value="foo"),
    )
    @patch("dbt_platform_helper.domain.copilot.load_application", autospec=True)
    def test_s3_cross_account_policies_called(
        self,
        mock_application,
        fakefs,
    ):
        dev_session = MagicMock(name="dev-session-mock")
        dev_session.profile_name = "foo"
        prod_session = MagicMock(name="prod-session-mock")
        prod_session.profile_name = "bar"
        client = MagicMock(name="client-mock")
        dev_session.client.return_value = client
        prod_session.client.return_value = client

        dev = Environment(
            name="development",
            account_id="000000000000",
            sessions={"000000000000": dev_session},
        )
        prod = Environment(
            name="production",
            account_id="111111111111",
            sessions={"111111111111": prod_session},
        )
        mock_application.return_value.environments = {
            "development": dev,
            "production": prod,
        }

        client.describe_key.return_value = {"KeyMetadata": {"Arn": "arn-for-kms-alias"}}

        create_test_manifests(S3_STORAGE_CONTENTS, fakefs)

        mocks = CopilotMocks()

        config = {
            "application": "test-app",
            "extensions": S3_STORAGE_CONTENTS,
            "environments": {"development": {}, "production": {}},
        }
        # Return value set explicitly so that calls can be asserted on the mock
        mocks.config_provider.apply_environment_defaults.return_value = config
        mocks.config_provider.load_and_validate_platform_config.return_value = config

        mocks.copilot_templating = Mock(spec=CopilotTemplating)
        mocks.copilot_templating.generate_cross_account_s3_policies.return_value = "TestData"

        mock_kms_instance = Mock()
        mock_kms_instance.describe_key.return_value = {"KeyMetadata": {"Arn": "arn-for-kms-alias"}}
        mock_kms = Mock()
        mock_kms.return_value = mock_kms_instance
        mocks.kms_provider = mock_kms

        Copilot(**mocks.params()).make_addons()

        exp = Copilot(**mocks.params())._get_extensions()
        exp["s3"]["environments"]["development"]["kms_key_arn"] = "arn-for-kms-alias"
        exp["s3"]["environments"]["production"]["kms_key_arn"] = "arn-for-kms-alias"

        mocks.config_provider.load_and_validate_platform_config.assert_called()
        mocks.config_provider.apply_environment_defaults.assert_called_with(config)
        mocks.copilot_templating.generate_cross_account_s3_policies.assert_called_with(
            {"development": {}, "production": {}}, exp
        )


@pytest.mark.parametrize(
    "service_type, expected",
    [
        ("Load Balanced Web Service", True),
        ("Backend Service", True),
        ("Request-Driven Web Service", True),
        ("Static Site", True),
        ("Worker Service", True),
        ("Scheduled Job", False),
        ("Foobar", False),
    ],
)
def test_is_service(fakefs, service_type, expected):
    file_path = "copilot/web/manifest.yml"
    manifest_contents = f"""
    type: {service_type}
    """
    fakefs.create_file(
        file_path,
        contents=" ".join([yaml.dump(yaml.safe_load(manifest_contents))]),
    )

    assert Copilot(**CopilotMocks().params())._is_service(PosixPath(file_path)) == expected


def test_is_service_empty_manifest(fakefs):
    file_path = "copilot/web/manifest.yml"
    fakefs.create_file(file_path)

    mocks = CopilotMocks()
    mocks.io = Mock(spec=ClickIOProvider)
    mocks.io.abort_with_error.side_effect = SystemExit(1)

    with pytest.raises(SystemExit):
        Copilot(**mocks.params())._is_service(PosixPath(file_path))

    mocks.io.abort_with_error.assert_called_with(
        f"No type defined in manifest file {file_path}; exiting"
    )


def test_generate_override_files(fakefs):
    """Test that, given a path to override files and an output directory,
    generate_override_files copies the required files to the output
    directory."""

    fakefs.create_file("templates/.gitignore")
    fakefs.create_file("templates/bin/code.ts")
    fakefs.create_file("templates/node_modules/package.ts")

    mocks = CopilotMocks()
    mocks.file_provider = FileProvider
    Copilot(**mocks.params())._generate_override_files(
        base_path=Path("."), file_path=Path("templates"), output_dir=Path("output")
    )

    assert ".gitignore" in os.listdir("/output")
    assert "code.ts" in os.listdir("/output/bin")
    assert "node_modules" not in os.listdir("/output")


def create_test_manifests(addon_file_contents, fakefs):
    content = yaml.dump({"application": "test-app", "extensions": addon_file_contents})
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=content)
    fakefs.create_file("copilot/web/manifest.yml", contents=yaml.dump(WEB_SERVICE_CONTENTS))
    fakefs.create_file("copilot/environments/development/manifest.yml")
    fakefs.create_file("copilot/environments/production/manifest.yml")
