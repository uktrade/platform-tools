import os
import shutil
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import boto3
import pytest
from click.testing import CliRunner
from freezegun import freeze_time
from moto import mock_ssm

from dbt_copilot_helper.commands.copilot import copilot
from dbt_copilot_helper.utils.aws import SSM_PATH
from tests.conftest import FIXTURES_DIR

REDIS_STORAGE_CONTENTS = """
redis:
  type: redis
  environments:
    default:
      engine: '6.2'
      plan: small
"""

RDS_POSTGRES_STORAGE_CONTENTS = """
rds:
  type: rds-postgres
  environments:
    default:
      plan: small-13-ha
"""

AURORA_POSTGRES_STORAGE_CONTENTS = """
aurora:
  type: aurora-postgres
  version: 14.4
  environments:
    default:
      min-capacity: 0.5
      max-capacity: 8
"""

OPENSEARCH_STORAGE_CONTENTS = """
opensearch:
  type: opensearch
  environments:
    default:
      plan: small
      engine: "2.3"
"""

S3_STORAGE_CONTENTS = """
my-s3-bucket:
  type: s3
  readonly: true
  services:
    - "web"
  environments:
    development:
      bucket-name: my-bucket-dev
"""

ADDON_CONFIG_FILENAME = "addons.yml"


class TestMakeAddonCommand:
    @pytest.mark.parametrize(
        "addon_file,expected_env_addons,expected_service_addons,expect_db_warning",
        [
            (
                "s3_addons.yml",
                ["my-s3-bucket.yml", "addons.parameters.yml", "vpc-endpoint.yml"],
                ["appconfig-ipfilter.yml", "my-s3-bucket.yml", "my-s3-bucket-bucket-access.yml"],
                False,
            ),
            (
                "opensearch_addons.yml",
                [
                    "my-opensearch.yml",
                    "my-opensearch-longer.yml",
                    "addons.parameters.yml",
                    "vpc-endpoint.yml",
                ],
                ["appconfig-ipfilter.yml"],
                False,
            ),
            (
                "rds_addons.yml",
                ["my-rds-db.yml", "addons.parameters.yml", "vpc-endpoint.yml"],
                ["appconfig-ipfilter.yml"],
                True,
            ),
            (
                "redis_addons.yml",
                ["my-redis.yml", "addons.parameters.yml", "vpc-endpoint.yml"],
                ["appconfig-ipfilter.yml"],
                False,
            ),
            (
                "aurora_addons.yml",
                ["my-aurora-db.yml", "addons.parameters.yml", "vpc-endpoint.yml"],
                ["appconfig-ipfilter.yml"],
                True,
            ),
            (
                "monitoring_addons.yml",
                ["monitoring.yml", "addons.parameters.yml", "vpc-endpoint.yml"],
                ["appconfig-ipfilter.yml"],
                False,
            ),
        ],
    )
    @freeze_time("2023-08-22 16:00:00")
    @patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    def test_make_addons_success(
        self,
        tmp_path,
        addon_file,
        expected_env_addons,
        expected_service_addons,
        expect_db_warning,
        validate_version,
    ):
        """Test that make_addons generates the expected directories and file
        contents."""
        # Arrange
        addons_dir = FIXTURES_DIR / "make_addons"
        shutil.copytree(addons_dir / "config", tmp_path, dirs_exist_ok=True)
        shutil.copy2(addons_dir / addon_file, tmp_path / ADDON_CONFIG_FILENAME)

        # Act
        os.chdir(tmp_path)
        result = CliRunner().invoke(copilot, ["make-addons"])

        assert (
            result.exit_code == 0
        ), f"The exit code should have been 0 (success) but was {result.exit_code}"
        validate_version.assert_called_once()
        db_warning = "Note: The key DATABASE_CREDENTIALS may need to be changed"
        assert (
            db_warning in result.stdout
        ) == expect_db_warning, "If we have a DB addon we expect a warning"

        expected_env_files = [
            Path("environments/addons", filename) for filename in expected_env_addons
        ]
        expected_service_files = [
            Path("web/addons", filename) for filename in expected_service_addons
        ]
        all_expected_files = expected_env_files + expected_service_files

        for f in all_expected_files:
            expected_file = Path(addons_dir, "expected", f)
            out_file = Path(addons_dir, "expected/environments/addons", "vpc-endpoint1.yml")

            if f.name == "vpc-endpoint.yml":
                with expected_file.open() as vpc_endpoint_file:
                    buffer = vpc_endpoint_file.readlines()

                with out_file.open("w") as vpc_endpoint_file:
                    print("addon_file", addon_file)
                    for line in buffer:
                        print(line)

                        if "EnvironmentSecurityGroup" in line:
                            vpc_endpoint_file.write(line)
                        elif addon_file == "rds_addons.yml" and "myRdsDbSecurityGroup" in line:
                            vpc_endpoint_file.write(line)
                        elif (
                            addon_file == "aurora_addons.yml"
                            and "myAuroraDbDBClusterSecurityGroup" in line
                        ):
                            vpc_endpoint_file.write(line)

                with out_file.open() as vpc_endpoint_file:
                    print("asdf", vpc_endpoint_file.readlines())

            expected = expected_file.read_text()
            actual = Path(tmp_path, "copilot", f).read_text()
            assert expected == actual, f"The file {f} did not have the expected content"

        copilot_dir = Path(tmp_path, "copilot")
        actual_files = [
            Path(d, f).relative_to(copilot_dir)
            for d, _, files in os.walk(copilot_dir)
            for f in files
        ]

        print("HERE>>>>>>", all_expected_files)
        print("ACTUAL FILES>>>>>>", actual_files)
        assert len(all_expected_files) + 2 == len(
            actual_files
        ), "We expect the actual filecount to match the expected with the addition of the two initial manifest.yml files"

    def test_exit_if_no_copilot_directory(self, fakefs, validate_version):
        fakefs.create_file(ADDON_CONFIG_FILENAME)

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        assert (
            result.output
            == "Cannot find copilot directory. Run this command in the root of the deployment "
            "repository.\n"
        )
        validate_version.assert_called_once()

    def test_exit_if_no_local_copilot_services(self, fakefs, validate_version):
        fakefs.create_file(ADDON_CONFIG_FILENAME)

        fakefs.create_file("copilot/environments/development/manifest.yml")

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        validate_version.assert_called_once()
        assert result.output == "No services found in ./copilot/; exiting\n"

    def test_exit_with_error_if_invalid_services(self, fakefs, validate_version):
        fakefs.create_file(
            ADDON_CONFIG_FILENAME,
            contents="""
invalid-entry:
    type: s3-policy
    services:
        - does-not-exist
        - also-does-not-exist
    environments:
        default:
            bucket-name: test-bucket
""",
        )

        fakefs.create_file("copilot/environments/development/manifest.yml")

        fakefs.create_file("copilot/web/manifest.yml")

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        validate_version.assert_called_once()
        assert (
            result.output
            == "Services listed in invalid-entry.services do not exist in ./copilot/\n"
        )

    def test_exit_with_error_if_invalid_environments(self, fakefs, validate_version):
        fakefs.create_file(
            ADDON_CONFIG_FILENAME,
            contents="""
invalid-environment:
    type: s3-policy
    environments:
        doesnotexist:
            bucket-name: test-bucket
""",
        )

        fakefs.create_file("copilot/environments/development/manifest.yml")

        fakefs.create_file("copilot/web/manifest.yml")

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        validate_version.assert_called_once()
        assert (
            result.output
            == "Environment keys listed in invalid-environment do not match ./copilot/environments\n"
        )

    def test_exit_if_services_key_invalid(self, fakefs, validate_version):
        """
        The services key can be set to a list of services, or '__all__' which
        denotes that it should be applied to all services.

        Any other string value results in an error.
        """

        fakefs.create_file(
            ADDON_CONFIG_FILENAME,
            contents="""
invalid-entry:
    type: s3-policy
    services: this-is-not-valid
    environments:
        default:
            bucket-name: test-bucket
""",
        )

        fakefs.create_file("copilot/environments/development/manifest.yml")

        fakefs.create_file("copilot/web/manifest.yml")

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        validate_version.assert_called_once()
        assert (
            result.output == "invalid-entry.services must be a list of service names or '__all__'\n"
        )

    def test_exit_if_no_local_copilot_environments(self, fakefs, validate_version):
        fakefs.create_file(ADDON_CONFIG_FILENAME)

        fakefs.create_file("copilot/web/manifest.yml")

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        validate_version.assert_called_once()
        assert result.output == "No environments found in ./copilot/environments; exiting\n"

    @pytest.mark.parametrize(
        "addon_file_contents, addon_type",
        [
            (REDIS_STORAGE_CONTENTS, "redis"),
            (RDS_POSTGRES_STORAGE_CONTENTS, "rds-postgres"),
            (AURORA_POSTGRES_STORAGE_CONTENTS, "aurora-postgres"),
            (OPENSEARCH_STORAGE_CONTENTS, "opensearch"),
            (S3_STORAGE_CONTENTS, "s3"),
        ],
    )
    @patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    def test_env_addons_parameters_file_with_different_addon_types(
        self, fakefs, addon_file_contents, addon_type, validate_version
    ):
        fakefs.create_file(
            ADDON_CONFIG_FILENAME,
            contents=addon_file_contents,
        )
        fakefs.create_file("copilot/web/manifest.yml")
        fakefs.create_file("copilot/environments/development/manifest.yml")

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 0
        validate_version.assert_called_once()

        assert (
            "File copilot/environments/addons/addons.parameters.yml overwritten" in result.output
        ), f"addons.parameters.yml should be included for {addon_type}"

    @pytest.mark.parametrize(
        "addon_file_contents, addon_type, secret_name",
        [
            (REDIS_STORAGE_CONTENTS, "redis", "REDIS"),
            (RDS_POSTGRES_STORAGE_CONTENTS, "rds-postgres", "RDS"),
            (AURORA_POSTGRES_STORAGE_CONTENTS, "aurora-postgres", "AURORA"),
        ],
    )
    @patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    def test_addon_instructions_with_postgres_addon_types(
        self, fakefs, addon_file_contents, addon_type, secret_name, validate_version
    ):
        fakefs.create_file(
            ADDON_CONFIG_FILENAME,
            contents=addon_file_contents,
        )
        fakefs.create_file("copilot/web/manifest.yml")
        fakefs.create_file("copilot/environments/development/manifest.yml")

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 0
        validate_version.assert_called_once()
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

    @patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    def test_appconfig_ip_filter_policy_is_applied_to_each_service_by_default(
        self, fakefs, validate_version
    ):
        services = ["web", "web-celery"]

        fakefs.create_file(ADDON_CONFIG_FILENAME)

        fakefs.create_file(
            "./copilot/environments/development/manifest.yml",
        )

        for service in services:
            fakefs.create_file(
                f"copilot/{service}/manifest.yml",
            )

        result = CliRunner().invoke(copilot, ["make-addons"])

        for service in services:
            path = Path(f"copilot/{service}/addons/appconfig-ipfilter.yml")
            assert path.exists()

        assert result.exit_code == 0
        validate_version.assert_called_once()


@mock_ssm
def test_get_secrets(validate_version):
    def _put_ssm_param(client, app, env, name, value):
        path = SSM_PATH.format(app=app, env=env, name=name)
        client.put_parameter(Name=path, Value=value, Type="String")

    ssm = boto3.client("ssm")

    secrets = [
        ["MY_SECRET", "testing"],
        ["MY_SECRET2", "hello"],
        ["MY_SECRET3", "world"],
    ]

    for name, value in secrets:
        _put_ssm_param(ssm, "myapp", "myenv", name, value)

    _put_ssm_param(ssm, "myapp", "anotherenv", "OTHER_ENV", "foobar")

    result = CliRunner().invoke(copilot, ["get-env-secrets", "myapp", "myenv"])

    for name, value in secrets:
        path = SSM_PATH.format(app="myapp", env="myenv", name=name)
        line = f"{path}: {value}"

        assert line in result.output

    assert SSM_PATH.format(app="myapp", env="anotherenv", name="OTHER_ENV") not in result.output
    validate_version.assert_called_once()
    assert result.exit_code == 0
