import json
import os
import re
from pathlib import Path
from pathlib import PosixPath
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import boto3
import pytest
import yaml
from click.testing import CliRunner
from freezegun import freeze_time
from moto import mock_aws

from dbt_platform_helper.commands.copilot import copilot
from dbt_platform_helper.commands.copilot import is_service
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.utils.application import Environment
from tests.platform_helper.conftest import FIXTURES_DIR
from tests.platform_helper.conftest import mock_aws_client

REDIS_STORAGE_CONTENTS = {
    "redis": {"type": "redis", "environments": {"default": {"engine": "6.2", "plan": "small"}}}
}

POSTGRES_STORAGE_CONTENTS = {
    "rds": {"type": "postgres", "version": 14.4, "environments": {"default": {"plan": "small-ha"}}}
}

AURORA_POSTGRES_STORAGE_CONTENTS = {
    "aurora": {
        "type": "aurora-postgres",
        "version": 14.4,
        "environments": {"*": {"min_capacity": 0.5, "max_capacity": 8}},
    }
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


class TestMakeAddonsCommand:
    @pytest.mark.parametrize(
        "kms_key_exists, kms_key_arn",
        (
            (True, "arn-for-kms-alias"),
            (False, "kms-key-not-found"),
        ),
    )
    @freeze_time("2023-08-22 16:00:00")
    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch(
        "dbt_platform_helper.commands.copilot.get_log_destination_arn",
        new=Mock(
            return_value='{"prod": "arn:cwl_log_destination_prod", "dev": "arn:dev_cwl_log_destination"}'
        ),
    )
    @patch(
        "dbt_platform_helper.utils.application.get_profile_name_from_account_id",
        new=Mock(return_value="foo"),
    )
    @patch("dbt_platform_helper.utils.application.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.copilot.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.copilot.load_application", autospec=True)
    @mock_aws
    def test_s3_kms_arn_is_rendered_in_template(
        self,
        mock_application,
        mock_get_session,
        mock_get_session2,
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
        mock_get_session.side_effect = [dev_session, prod_session]
        mock_get_session2.side_effect = [dev_session, prod_session]

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
        client.get_parameters_by_path.side_effect = [
            {
                "Parameters": [
                    {
                        "Name": "/copilot/applications/test-app/environments/development",
                        "Type": "SecureString",
                        "Value": json.dumps(
                            {
                                "name": "development",
                                "accountID": "000000000000",
                            }
                        ),
                    }
                ]
            },
            {
                "Parameters": [
                    {
                        "Name": "/copilot/applications/test-app/components/web",
                        "Type": "SecureString",
                        "Value": json.dumps(
                            {
                                "app": "test-app",
                                "name": "web",
                                "type": "Load Balanced Web Service",
                            }
                        ),
                    }
                ]
            },
        ]

        if kms_key_exists:
            client.describe_key.return_value = {"KeyMetadata": {"Arn": kms_key_arn}}
        else:
            client.exceptions.NotFoundException = boto3.client("kms").exceptions.NotFoundException
            client.describe_key.side_effect = boto3.client("kms").exceptions.NotFoundException(
                error_response={}, operation_name="describe_key"
            )

        fakefs.add_real_file(FIXTURES_DIR / "valid_workspace.yml", False, "copilot/.workspace")

        create_test_manifests(S3_STORAGE_CONTENTS, fakefs)

        CliRunner().invoke(copilot, ["make-addons"])

        s3_addon = yaml.safe_load(Path(f"/copilot/web/addons/s3.yml").read_text())

        assert (
            s3_addon["Mappings"]["s3EnvironmentConfigMap"]["development"]["KmsKeyArn"]
            == kms_key_arn
        )
        dev_session.client.assert_called_with("kms")
        prod_session.client.assert_called_with("kms")
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
    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch(
        "dbt_platform_helper.commands.copilot.get_log_destination_arn",
        new=Mock(
            return_value='{"prod": "arn:cwl_log_destination_prod", "dev": "arn:dev_cwl_log_destination"}'
        ),
    )
    @patch("dbt_platform_helper.commands.copilot.get_aws_session_or_abort")
    @mock_aws
    def test_terraform_compatible_make_addons_success(
        self,
        mock_get_session,
        fakefs,
        addon_file,
        expected_service_addons,
    ):
        """Test that make_addons generates the expected directories and file
        contents."""
        # Arrange
        mock_aws_client(mock_get_session)

        addons_dir = FIXTURES_DIR / "make_addons"
        fakefs.add_real_directory(
            addons_dir / "config/copilot", read_only=False, target_path="copilot"
        )
        fakefs.add_real_file(
            addons_dir / addon_file, read_only=False, target_path=PLATFORM_CONFIG_FILE
        )
        fakefs.add_real_directory(Path(addons_dir, "expected"), target_path="expected")

        # Act
        result = CliRunner().invoke(copilot, ["make-addons"])

        assert (
            result.exit_code == 0
        ), f"The exit code should have been 0 (success) but was {result.exit_code}"

        assert ">>> Generating Terraform compatible addons CloudFormation" in result.stdout

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
        assert f"{env_override_file} created" in result.stdout

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
    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch(
        "dbt_platform_helper.commands.copilot.get_log_destination_arn",
        new=Mock(
            return_value='{"prod": "arn:cwl_log_destination_prod", "dev": "arn:dev_cwl_log_destination"}'
        ),
    )
    @patch("dbt_platform_helper.commands.copilot.get_aws_session_or_abort")
    def test_make_addons_removes_old_addons_files(
        self,
        mock_get_session,
        fakefs,
    ):
        """Tests that old addons files are cleaned up before generating new
        ones."""

        # Arrange
        mock_aws_client(mock_get_session)
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
        CliRunner().invoke(copilot, ["make-addons"])

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

    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    def test_exit_if_no_config_file(self, fakefs):
        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        assert (
            f"`{PLATFORM_CONFIG_FILE}` is missing. Please check it exists and you are in the root directory of your deployment project."
            in result.output
        )

    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    def test_exit_if_no_local_copilot_services(self, fakefs):
        fakefs.create_file(PLATFORM_CONFIG_FILE)

        fakefs.create_file("copilot/environments/development/manifest.yml")

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        assert "No services found in ./copilot/; exiting" in result.output

    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    @mock_aws
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

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        assert (
            "Services listed in invalid-entry.services do not exist in ./copilot/" in result.output
        )

    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    @mock_aws
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

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        assert re.match(
            r"(?s).*example-invalid-file.*environments.*default.*Wrong key 'no_such_key'",
            result.output,
        )

    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    @mock_aws
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

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        assert (
            "Environment keys listed in invalid-environment do not match those defined in ./copilot/environments"
            in result.output
        )
        assert "Missing environments: alsodoesnotexist, doesnotexist" in result.output
        assert (
            "Environment keys listed in invalid-environment-2 do not match those defined in ./copilot/environments"
            in result.output
        )
        assert "Missing environments: andanotherdoesnotexist" in result.output
        assert (
            "Services listed in invalid-environment.services do not exist in ./copilot/"
            in result.output
        )

    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    @mock_aws
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

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        assert f"Errors found in {PLATFORM_CONFIG_FILE}:" in result.output
        assert "'Delete' does not match 'ThisIsInvalid'" in result.output
        assert "Names cannot be prefixed 'sthree-'" in result.output
        assert "Names cannot be suffixed '-s3alias'" in result.output
        assert "Names cannot contain two adjacent periods" in result.output
        assert "Names can only contain the characters 0-9, a-z, '.' and '-'." in result.output

    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
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

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        assert "Key 'services' error:" in result.output
        assert "'__all__' does not match 'this-is-not-valid'" in result.output
        assert "'this-is-not-valid' should be instance of 'list'" in result.output

    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    def test_exit_if_no_local_copilot_environments(self, fakefs):
        fakefs.create_file(PLATFORM_CONFIG_FILE)

        fakefs.create_file("copilot/web/manifest.yml", contents=yaml.dump(WEB_SERVICE_CONTENTS))

        fakefs.add_real_file(FIXTURES_DIR / "valid_workspace.yml", False, "copilot/.workspace")

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        assert "No environments found in ./copilot/environments; exiting" in result.output

    @pytest.mark.parametrize(
        "addon_config, addon_type, secret_name",
        [
            (REDIS_STORAGE_CONTENTS, "redis", "REDIS"),
            (POSTGRES_STORAGE_CONTENTS, "postgres", "RDS"),
            (AURORA_POSTGRES_STORAGE_CONTENTS, "aurora-postgres", "AURORA"),
        ],
    )
    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    @patch(
        "dbt_platform_helper.commands.copilot.get_log_destination_arn",
        new=Mock(
            return_value='{"prod": "arn:cwl_log_destination_prod", "dev": "arn:dev_cwl_log_destination"}'
        ),
    )
    @patch("dbt_platform_helper.commands.copilot.get_aws_session_or_abort", new=Mock())
    def test_addon_instructions_with_postgres_addon_types(
        self, fakefs, addon_config, addon_type, secret_name
    ):
        fakefs.add_real_file(FIXTURES_DIR / "valid_workspace.yml", False, "copilot/.workspace")
        create_test_manifests(addon_config, fakefs)

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 0
        if addon_type == "redis":
            assert (
                "DATABASE_CREDENTIALS" not in result.output
            ), f"DATABASE_CREDENTIALS should not be included for {addon_type}"
        else:
            assert (
                "DATABASE_CREDENTIALS" in result.output
            ), f"DATABASE_CREDENTIALS should be included for {addon_type}"
            assert (
                "secretsmanager: /copilot/${COPILOT_APPLICATION_NAME}/${COPILOT_ENVIRONMENT_NAME}/secrets/"
                f"{secret_name}" in result.output
            )

    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch(
        "dbt_platform_helper.commands.copilot.get_log_destination_arn",
        new=Mock(
            return_value='{"prod": "arn:cwl_log_destination_prod", "dev": "arn:dev_cwl_log_destination"}'
        ),
    )
    @patch("dbt_platform_helper.commands.copilot.get_aws_session_or_abort")
    def test_appconfig_ip_filter_policy_is_applied_to_each_service_by_default(
        self, mock_get_aws_session_or_abort, fakefs
    ):
        services = ["web", "web-celery"]
        fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump({"extensions": {}}))
        fakefs.add_real_file(FIXTURES_DIR / "valid_workspace.yml", False, "copilot/.workspace")

        fakefs.create_file(
            "./copilot/environments/development/manifest.yml",
        )

        for service in services:
            fakefs.create_file(
                f"copilot/{service}/manifest.yml", contents=yaml.dump(WEB_SERVICE_CONTENTS)
            )

        result = CliRunner().invoke(copilot, ["make-addons"])

        for service in services:
            for custom_addon in ["appconfig-ipfilter.yml", "subscription-filter.yml"]:
                path = Path(f"copilot/{service}/addons/{custom_addon}")
                assert path.exists()

        assert result.exit_code == 0


@pytest.mark.parametrize(
    "service_type, expected",
    [
        ("Load Balanced Web Service", True),
        ("Backend Service", True),
        ("Request-Driven Web Service", True),
        ("Static Site", True),
        ("Worker Service", True),
        ("Scheduled Job", False),
    ],
)
def test_is_service(fakefs, service_type, expected):
    manifest_contents = f"""
    type: {service_type}
    """
    fakefs.create_file(
        "copilot/web/manifest.yml",
        contents=" ".join([yaml.dump(yaml.safe_load(manifest_contents))]),
    )

    assert is_service(PosixPath("copilot/web/manifest.yml")) == expected


def test_is_service_empty_manifest(fakefs, capfd):
    file_path = "copilot/web/manifest.yml"
    fakefs.create_file(file_path)

    with pytest.raises(SystemExit) as excinfo:
        is_service(PosixPath(file_path))

    assert excinfo.value.code == 1
    assert f"No type defined in manifest file {file_path}; exiting" in capfd.readouterr().out


def create_test_manifests(addon_file_contents, fakefs):
    content = yaml.dump({"extensions": addon_file_contents})
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=content)
    fakefs.create_file("copilot/web/manifest.yml", contents=yaml.dump(WEB_SERVICE_CONTENTS))
    fakefs.create_file("copilot/environments/development/manifest.yml")
    fakefs.create_file("copilot/environments/production/manifest.yml")
