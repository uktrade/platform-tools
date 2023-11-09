import os
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import boto3
import pytest
import yaml
from click.testing import CliRunner
from freezegun import freeze_time
from moto import mock_ssm
from yaml import dump

from dbt_copilot_helper.commands.copilot import copilot
from dbt_copilot_helper.utils.aws import SSM_PATH
from tests.copilot_helper.conftest import FIXTURES_DIR

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
  version: 14.4
  environments:
    default:
      plan: small-ha
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
                [
                    "my-s3-bucket.yml",
                    "my-s3-bucket-with-an-object.yml",
                    "addons.parameters.yml",
                    "vpc.yml",
                ],
                [
                    "appconfig-ipfilter.yml",
                    "my-s3-bucket.yml",
                    "my-s3-bucket-with-an-object.yml",
                    "my-s3-bucket-bucket-access.yml",
                ],
                False,
            ),
            (
                "opensearch_addons.yml",
                [
                    "my-opensearch.yml",
                    "my-opensearch-longer.yml",
                    "addons.parameters.yml",
                    "vpc.yml",
                ],
                ["appconfig-ipfilter.yml"],
                False,
            ),
            (
                "rds_addons.yml",
                ["my-rds-db.yml", "addons.parameters.yml", "vpc.yml"],
                ["appconfig-ipfilter.yml"],
                True,
            ),
            (
                "redis_addons.yml",
                ["my-redis.yml", "addons.parameters.yml", "vpc.yml"],
                ["appconfig-ipfilter.yml"],
                False,
            ),
            (
                "aurora_addons.yml",
                ["my-aurora-db.yml", "addons.parameters.yml", "vpc.yml"],
                ["appconfig-ipfilter.yml"],
                True,
            ),
            (
                "monitoring_addons.yml",
                ["monitoring.yml", "addons.parameters.yml", "vpc.yml"],
                ["appconfig-ipfilter.yml"],
                False,
            ),
        ],
    )
    @freeze_time("2023-08-22 16:00:00")
    @patch(
        "dbt_copilot_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=True),
    )
    @patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    def test_make_addons_success(
        self,
        fakefs,
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
        fakefs.add_real_directory(
            addons_dir / "config/copilot", read_only=False, target_path="copilot"
        )
        fakefs.add_real_file(
            addons_dir / addon_file, read_only=False, target_path=ADDON_CONFIG_FILENAME
        )
        fakefs.add_real_directory(Path(addons_dir, "expected"), target_path="expected")

        # Act
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
            expected_file = Path("expected", f)
            if f.name == "vpc.yml":
                if addon_file == "rds_addons.yml":
                    vpc_file = "rds-postgres"
                elif addon_file == "aurora_addons.yml":
                    vpc_file = "aurora-postgres"
                else:
                    vpc_file = "default"

                expected_file = Path(
                    "expected/environments/addons",
                    f"vpc-{vpc_file}.yml",
                )

            expected = expected_file.read_text()
            actual = Path("copilot", f).read_text()
            assert actual == expected, f"The file {f} did not have the expected content"

        expected_file = Path("expected/environments/overrides/cfn.patches.yml")

        expected = expected_file.read_text()
        actual = Path("copilot/environments/overrides/cfn.patches.yml").read_text()
        assert actual == expected, f"The environment overrides did not have the expected content"

        copilot_dir = Path("copilot")
        actual_files = [
            Path(d, f).relative_to(copilot_dir)
            for d, _, files in os.walk(copilot_dir)
            for f in files
        ]

        assert (
            len(actual_files) == len(all_expected_files) + 3
        ), "The actual filecount should be expected files plus 2 initial manifest.yml and override files"

    @freeze_time("2023-08-22 16:00:00")
    @patch(
        "dbt_copilot_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    @patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    def test_make_addons_removes_old_addons_files(
        self,
        fakefs,
    ):
        """Tests that old addons files are cleaned up before generating new
        ones."""
        # Arrange
        addons_dir = FIXTURES_DIR / "make_addons"
        fakefs.add_real_directory(
            addons_dir / "config/copilot", read_only=False, target_path="copilot"
        )
        fakefs.add_real_file(
            addons_dir / "redis_addons.yml", read_only=False, target_path=ADDON_CONFIG_FILENAME
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
            fakefs.add_real_file(
                addons_dir / "expected" / f, read_only=False, target_path=Path("copilot", f)
            )

        # Act
        CliRunner().invoke(copilot, ["make-addons"])

        # Assert
        expected_env_files = [
            Path("environments/addons", f)
            for f in ["my-redis.yml", "addons.parameters.yml", "vpc.yml"]
        ]
        expected_service_files = [Path("web/addons/appconfig-ipfilter.yml")]
        all_expected_files = expected_env_files + expected_service_files

        for f in all_expected_files:
            expected_file = Path(
                "expected", f if not f.name == "vpc.yml" else "environments/addons/vpc-default.yml"
            )
            expected = expected_file.read_text()
            actual = Path("copilot", f).read_text()
            assert actual == expected, f"The file {f} did not have the expected content"

        for f in old_addon_files:
            path = Path("copilot", f)
            assert not path.exists()

    @pytest.mark.parametrize(
        "deletion_policy,deletion_policy_override,expected_deletion_policy",
        [
            (None, None, "Delete"),
            ("Delete", None, "Delete"),
            (None, "Delete", "Delete"),
            ("Retain", None, "Retain"),
            (None, "Retain", "Retain"),
            ("Delete", "Retain", "Retain"),
            ("Retain", "Delete", "Delete"),
        ],
    )
    @freeze_time("2023-08-22 16:00:00")
    @patch(
        "dbt_copilot_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    @patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    def test_make_addons_s3_deletion_policy(
        self, fakefs, deletion_policy, deletion_policy_override, expected_deletion_policy
    ):
        """Test that deletion policy defaults and overrides are applied
        correctly."""
        addon_file_contents = {
            "my-s3-bucket": {
                "type": "s3",
                "readonly": True,
                "deletion-policy": deletion_policy,
                "services": [
                    "web",
                ],
                "environments": {
                    "development": {
                        "bucket-name": "my-bucket-dev",
                        "deletion-policy": deletion_policy_override,
                    },
                },
            }
        }
        if not deletion_policy:
            del addon_file_contents["my-s3-bucket"]["deletion-policy"]
        if not deletion_policy_override:
            del addon_file_contents["my-s3-bucket"]["environments"]["development"][
                "deletion-policy"
            ]
        create_test_manifests(dump(addon_file_contents), fakefs)

        CliRunner().invoke(copilot, ["make-addons"])

        manifest = yaml.safe_load(Path("/copilot/environments/addons/my-s3-bucket.yml").read_text())
        assert (
            manifest["Mappings"]["myS3BucketEnvironmentConfigMap"]["development"]["DeletionPolicy"]
            == expected_deletion_policy
        )

    @patch(
        "dbt_copilot_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=True),
    )
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

    @patch(
        "dbt_copilot_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=True),
    )
    def test_exit_if_no_local_copilot_services(self, fakefs, validate_version):
        fakefs.create_file(ADDON_CONFIG_FILENAME)

        fakefs.create_file("copilot/environments/development/manifest.yml")

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        validate_version.assert_called_once()
        assert result.output == "No services found in ./copilot/; exiting\n"

    @patch(
        "dbt_copilot_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=True),
    )
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

    @patch(
        "dbt_copilot_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=True),
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

    @patch(
        "dbt_copilot_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=True),
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

    @patch(
        "dbt_copilot_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=True),
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
        ],
    )
    @patch(
        "dbt_copilot_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=True),
    )
    @patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    def test_env_addons_parameters_file_included_with_different_addon_types(
        self, fakefs, addon_file_contents, addon_type, validate_version
    ):
        create_test_manifests(addon_file_contents, fakefs)

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 0
        validate_version.assert_called_once()
        assert (
            "File copilot/environments/addons/addons.parameters.yml created" in result.output
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
    @patch(
        "dbt_copilot_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=True),
    )
    def test_addon_instructions_with_postgres_addon_types(
        self, fakefs, addon_file_contents, addon_type, secret_name, validate_version
    ):
        create_test_manifests(addon_file_contents, fakefs)

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

    @patch(
        "dbt_copilot_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=True),
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
@patch(
    "dbt_copilot_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
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


def create_test_manifests(addon_file_contents, fakefs):
    fakefs.create_file(
        ADDON_CONFIG_FILENAME,
        contents=addon_file_contents,
    )
    fakefs.create_file("copilot/web/manifest.yml")
    fakefs.create_file("copilot/environments/development/manifest.yml")
