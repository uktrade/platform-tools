import json
import os
import re
from pathlib import Path
from pathlib import PosixPath
from unittest.mock import Mock
from unittest.mock import patch

import boto3
import pytest
import yaml
from botocore.exceptions import ClientError
from click.testing import CliRunner
from freezegun import freeze_time
from moto import mock_aws
from yaml import dump

from dbt_platform_helper.commands.copilot import copilot
from dbt_platform_helper.commands.copilot import is_service
from dbt_platform_helper.utils.validation import BUCKET_NAME_IN_USE_TEMPLATE
from tests.platform_helper.conftest import FIXTURES_DIR
from tests.platform_helper.conftest import mock_aws_client

REDIS_STORAGE_CONTENTS = """
redis:
  type: redis
  environments:
    default:
      engine: '6.2'
      plan: small
"""

POSTGRES_STORAGE_CONTENTS = """
rds:
  type: postgres
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
    "*":
      min_capacity: 0.5
      max_capacity: 8
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
s3:
  type: s3
  readonly: true
  services:
    - "web"
  environments:
    development:
      bucket_name: my-bucket-dev
"""

WEB_SERVICE_CONTENTS = """
name: web
type: Load Balanced Web Service
"""

EXTENSION_CONFIG_FILENAME = "extensions.yml"


class TestTerraformEnabledMakeAddonCommand:
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
    @mock_aws
    def test_s3_kms_arn_is_rendered_in_template(
        self, mock_get_session, mock_get_session2, fakefs, kms_key_exists, kms_key_arn
    ):
        client = mock_aws_client(mock_get_session)
        mock_aws_client(mock_get_session2, client)

        client.get_parameters_by_path.return_value = {
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
        }

        if kms_key_exists:
            client.describe_key.return_value = {"KeyMetadata": {"Arn": kms_key_arn}}
        else:
            client.exceptions.NotFoundException = boto3.client("kms").exceptions.NotFoundException
            client.describe_key.side_effect = boto3.client("kms").exceptions.NotFoundException(
                error_response={}, operation_name="describe_key"
            )

        fakefs.create_dir("./terraform")
        fakefs.add_real_file(FIXTURES_DIR / "valid_workspace.yml", False, "copilot/.workspace")

        create_test_manifests([S3_STORAGE_CONTENTS], fakefs)

        CliRunner().invoke(copilot, ["make-addons"])

        s3_addon = yaml.safe_load(Path(f"/copilot/web/addons/s3.yml").read_text())

        assert (
            s3_addon["Mappings"]["s3EnvironmentConfigMap"]["development"]["KmsKeyArn"]
            == kms_key_arn
        )

    @pytest.mark.parametrize(
        "addon_file, expected_service_addons",
        [
            (
                "s3_addons.yml",
                [
                    "appconfig-ipfilter.yml",
                    "subscription-filter.yml",
                    "my-s3-bucket.yml",
                    "my-s3-bucket-with-an-object.yml",
                    "my-s3-bucket-bucket-access.yml",
                ],
            ),
            (
                "opensearch_addons.yml",
                ["appconfig-ipfilter.yml", "subscription-filter.yml"],
            ),
            (
                "rds_addons.yml",
                ["appconfig-ipfilter.yml", "subscription-filter.yml"],
            ),
            (
                "redis_addons.yml",
                ["appconfig-ipfilter.yml", "subscription-filter.yml"],
            ),
            (
                "monitoring_addons.yml",
                ["appconfig-ipfilter.yml", "subscription-filter.yml"],
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
            addons_dir / addon_file, read_only=False, target_path=EXTENSION_CONFIG_FILENAME
        )
        fakefs.add_real_directory(Path(addons_dir, "expected"), target_path="expected")

        # make-addons will generate terraform compatible addons if it detects a ./terraform directory
        fakefs.create_dir("./terraform")

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

        assert not any(
            Path("./copilot/environments/addons/").iterdir()
        ), "./copilot/environments/addons/ should be empty"

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


class TestMakeAddonCommand:
    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=True),
    )
    def test_validate_version_called_once(self, validate_version):
        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        validate_version.assert_called_once()

    @pytest.mark.parametrize(
        "addon_file, expected_env_addons, expected_service_addons, expect_db_warning",
        [
            (
                "s3_addons.yml",
                [
                    "my-s3-bucket.yml",
                    "my-s3-bucket-with-an-object.yml",
                    "addons.parameters.yml",
                    "monitoring.yml",
                    "vpc.yml",
                ],
                [
                    "appconfig-ipfilter.yml",
                    "subscription-filter.yml",
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
                    "monitoring.yml",
                    "vpc.yml",
                ],
                ["appconfig-ipfilter.yml", "subscription-filter.yml"],
                False,
            ),
            (
                "rds_addons.yml",
                ["my-rds-db.yml", "addons.parameters.yml", "monitoring.yml", "vpc.yml"],
                ["appconfig-ipfilter.yml", "subscription-filter.yml"],
                True,
            ),
            (
                "redis_addons.yml",
                ["my-redis.yml", "addons.parameters.yml", "monitoring.yml", "vpc.yml"],
                ["appconfig-ipfilter.yml", "subscription-filter.yml"],
                False,
            ),
            (
                "aurora_addons.yml",
                ["my-aurora-db.yml", "addons.parameters.yml", "monitoring.yml", "vpc.yml"],
                ["appconfig-ipfilter.yml", "subscription-filter.yml"],
                True,
            ),
            (
                "monitoring_addons.yml",
                ["monitoring.yml", "addons.parameters.yml", "vpc.yml"],
                ["appconfig-ipfilter.yml", "subscription-filter.yml"],
                False,
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
    def test_make_addons_success(
        self,
        mock_get_session,
        fakefs,
        addon_file,
        expected_env_addons,
        expected_service_addons,
        expect_db_warning,
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
            addons_dir / addon_file, read_only=False, target_path=EXTENSION_CONFIG_FILENAME
        )
        fakefs.add_real_directory(Path(addons_dir, "expected"), target_path="expected")

        # Act
        result = CliRunner().invoke(copilot, ["make-addons"])

        assert (
            result.exit_code == 0
        ), f"The exit code should have been 0 (success) but was {result.exit_code}"
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

            if f.name == "addons.parameters.yml" and addon_file in [
                "rds_addons.yml",
                "aurora_addons.yml",
            ]:
                expected_file = Path(
                    "expected/environments/addons",
                    "addons.parameters.rds.yml",
                )

            expected = yaml.safe_load(expected_file.read_text())
            actual = yaml.safe_load(Path("copilot", f).read_text())

            assert sorted(expected) == sorted(
                actual
            ), f"The file {f} did not have the expected content"

            assert actual == expected

        env_override_files = setup_override_files_for_environments()
        for file in env_override_files:
            assert f"{file} created" in result.stdout
        all_expected_files += env_override_files

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
    @mock_aws
    @patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
    def test_make_addons_success_but_warns_when_bucket_name_in_use(self, mock_get_session, fakefs):
        client = mock_aws_client(mock_get_session)
        client.head_bucket.side_effect = ClientError({"Error": {"Code": "400"}}, "HeadBucket")
        """Test that make_addons generates the expected directories and file
        contents."""
        # Arrange
        addons_dir = FIXTURES_DIR / "make_addons"
        fakefs.add_real_directory(
            addons_dir / "config/copilot", read_only=False, target_path="copilot"
        )
        fakefs.add_real_file(
            addons_dir / "s3_addons.yml", read_only=False, target_path=EXTENSION_CONFIG_FILENAME
        )
        fakefs.add_real_directory(Path(addons_dir, "expected"), target_path="expected")

        # Act
        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 0
        assert BUCKET_NAME_IN_USE_TEMPLATE.format("my-bucket") in result.output

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
            target_path=EXTENSION_CONFIG_FILENAME,
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
                addons_dir / "expected" / f,
                read_only=False,
                target_path=Path("copilot", f),
            )

        # Act
        CliRunner().invoke(copilot, ["make-addons"])

        # Assert
        expected_env_files = [
            Path("environments/addons", f)
            for f in ["my-redis.yml", "addons.parameters.yml", "vpc.yml"]
        ]
        expected_service_files = [
            Path("web/addons", f) for f in ["appconfig-ipfilter.yml", "subscription-filter.yml"]
        ]
        all_expected_files = expected_env_files + expected_service_files

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
            assert not path.exists()

    @pytest.mark.parametrize(
        "addon_file, addon_name",
        [
            (S3_STORAGE_CONTENTS, "s3"),
            (REDIS_STORAGE_CONTENTS, "redis"),
            (POSTGRES_STORAGE_CONTENTS, "rds"),
            (AURORA_POSTGRES_STORAGE_CONTENTS, "aurora"),
            (OPENSEARCH_STORAGE_CONTENTS, "opensearch"),
        ],
    )
    @pytest.mark.parametrize(
        "deletion_policy_override, expected_deletion_policy",
        [
            (None, "Delete"),
            ("Retain", "Retain"),
            ("Delete", "Delete"),
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
    @patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort", new=Mock())
    @mock_aws
    def test_make_addons_deletion_policy(
        self,
        fakefs,
        addon_file,
        addon_name,
        deletion_policy_override,
        expected_deletion_policy,
    ):
        """Test that deletion policy defaults and overrides are applied
        correctly."""

        fakefs.add_real_file(FIXTURES_DIR / "valid_workspace.yml", False, "copilot/.workspace")

        addon_file_contents = yaml.safe_load(addon_file)
        if deletion_policy_override:
            for env in addon_file_contents[addon_name]["environments"]:
                addon_file_contents[addon_name]["environments"][env][
                    "deletion_policy"
                ] = deletion_policy_override

        create_test_manifests([dump(addon_file_contents)], fakefs)

        CliRunner().invoke(copilot, ["make-addons"])

        manifest = yaml.safe_load(
            Path(f"/copilot/environments/addons/{addon_name}.yml").read_text()
        )
        assert (
            manifest["Mappings"][f"{addon_name}EnvironmentConfigMap"]["development"][
                "DeletionPolicy"
            ]
            == expected_deletion_policy
        )

    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    def test_exit_if_no_copilot_directory(self, fakefs):
        fakefs.create_file(EXTENSION_CONFIG_FILENAME)

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        assert (
            "Cannot find copilot directory. Run this command in the root of the deployment repository."
            in result.output
        )

    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    def test_exit_if_no_local_copilot_services(self, fakefs):
        fakefs.create_file(EXTENSION_CONFIG_FILENAME)

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
            EXTENSION_CONFIG_FILENAME,
            contents="""
invalid-entry:
    type: s3-policy
    services:
        - does-not-exist
        - also-does-not-exist
    environments:
        default:
            bucket_name: test-bucket
""",
        )

        fakefs.create_file("copilot/environments/development/manifest.yml")

        fakefs.create_file(
            "copilot/web/manifest.yml",
            contents=" ".join([yaml.dump(yaml.safe_load(WEB_SERVICE_CONTENTS))]),
        )

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
            EXTENSION_CONFIG_FILENAME,
            contents="""
example-invalid-file:
    type: s3
    environments:
        default:
            bucket_name: test-bucket
            no_such_key: bad-key
""",
        )

        fakefs.create_file("copilot/environments/development/manifest.yml")
        fakefs.create_file(
            "copilot/web/manifest.yml",
            contents=" ".join([yaml.dump(yaml.safe_load(WEB_SERVICE_CONTENTS))]),
        )

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
    def test_exit_with_error_if_invalid_environments(self, fakefs):
        fakefs.create_file(
            EXTENSION_CONFIG_FILENAME,
            contents="""
invalid-environment:
    type: s3-policy
    environments:
        doesnotexist:
            bucket_name: test-bucket
        alsodoesnotexist:
            bucket_name: test-bucket-2
""",
        )

        fakefs.create_file("copilot/environments/development/manifest.yml")

        fakefs.create_file(
            "copilot/web/manifest.yml",
            contents=" ".join([yaml.dump(yaml.safe_load(WEB_SERVICE_CONTENTS))]),
        )

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        assert (
            "Environment keys listed in invalid-environment do not match those defined in ./copilot/environments"
            in result.output
        )
        assert "Missing environments: alsodoesnotexist, doesnotexist" in result.output

    @patch(
        "dbt_platform_helper.utils.versioning.running_as_installed_package",
        new=Mock(return_value=False),
    )
    @mock_aws
    def test_exit_with_multiple_errors(self, fakefs):
        fakefs.create_file(
            EXTENSION_CONFIG_FILENAME,
            contents="""
my-s3-bucket-1:
  type: s3
  environments:
    dev:
      bucket_name: sthree-one..TWO-s3alias # Many naming errors

my-s3-bucket-2:
  type: s3
  environments:
    dev:
      bucket_name: charles
      deletion_policy: ThisIsInvalid # Should be a valid policy name.
""",
        )

        fakefs.create_file("copilot/environments/development/manifest.yml")

        fakefs.create_file(
            "copilot/web/manifest.yml",
            contents=" ".join([yaml.dump(yaml.safe_load(WEB_SERVICE_CONTENTS))]),
        )

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        assert "Errors found in extensions.yml:" in result.output
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
            EXTENSION_CONFIG_FILENAME,
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

        fakefs.create_file(
            "copilot/web/manifest.yml",
            contents=" ".join([yaml.dump(yaml.safe_load(WEB_SERVICE_CONTENTS))]),
        )

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
        fakefs.create_file(EXTENSION_CONFIG_FILENAME)

        fakefs.create_file(
            "copilot/web/manifest.yml",
            contents=" ".join([yaml.dump(yaml.safe_load(WEB_SERVICE_CONTENTS))]),
        )

        fakefs.add_real_file(FIXTURES_DIR / "valid_workspace.yml", False, "copilot/.workspace")

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 1
        assert "No environments found in ./copilot/environments; exiting" in result.output

    @pytest.mark.parametrize(
        "addon_file_contents, has_postgres_addon",
        [
            ([REDIS_STORAGE_CONTENTS], False),
            ([POSTGRES_STORAGE_CONTENTS], True),
            ([AURORA_POSTGRES_STORAGE_CONTENTS], True),
            ([OPENSEARCH_STORAGE_CONTENTS], False),
            # Check when we have a mix of addons...
            (
                [
                    POSTGRES_STORAGE_CONTENTS,
                    OPENSEARCH_STORAGE_CONTENTS,
                    S3_STORAGE_CONTENTS,
                ],
                True,
            ),
        ],
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
    @patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort", new=Mock())
    @mock_aws
    def test_addons_parameters_file_included_with_required_parameters_for_the_addon_types(
        self, fakefs, addon_file_contents, has_postgres_addon
    ):
        def assert_in_addons_parameters_as_required(
            checks, addons_parameters_contents, should_include
        ):
            should_or_should_not_string = "should"
            if not should_include:
                should_or_should_not_string += " not"
            for check in checks:
                assert (
                    check in addons_parameters_contents
                ) == should_include, (
                    f"'{check}' {should_or_should_not_string} be included in addons.parameters.yml"
                )

        fakefs.add_real_file(FIXTURES_DIR / "valid_workspace.yml", False, "copilot/.workspace")
        create_test_manifests(addon_file_contents, fakefs)

        result = CliRunner().invoke(copilot, ["make-addons"])

        assert result.exit_code == 0
        assert (
            "File copilot/environments/addons/addons.parameters.yml created" in result.output
        ), "addons.parameters.yml should be included"
        addons_parameters_contents = Path(
            "/copilot/environments/addons/addons.parameters.yml"
        ).read_text()
        assert_in_addons_parameters_as_required(
            checks=[
                "EnvironmentSecurityGroup: !Ref EnvironmentSecurityGroup",
                "PrivateSubnets: !Join [ ',', [ !Ref PrivateSubnet1, !Ref PrivateSubnet2, ] ]",
                "PublicSubnets: !Join [ ',', [ !Ref PublicSubnet1, !Ref PublicSubnet2, ] ]",
                "VpcId: !Ref VPC",
            ],
            addons_parameters_contents=addons_parameters_contents,
            should_include=True,
        )
        assert_in_addons_parameters_as_required(
            checks=[
                "DefaultPublicRoute: !Ref DefaultPublicRoute",
                "InternetGateway: !Ref InternetGateway",
                "InternetGatewayAttachment: !Ref InternetGatewayAttachment",
                "PublicRouteTable: !Ref PublicRouteTable",
                "PublicSubnet1RouteTableAssociation: !Ref PublicSubnet1RouteTableAssociation",
                "PublicSubnet2RouteTableAssociation: !Ref PublicSubnet2RouteTableAssociation",
            ],
            addons_parameters_contents=addons_parameters_contents,
            should_include=has_postgres_addon,
        )

    @pytest.mark.parametrize(
        "addon_file_contents, addon_type, secret_name",
        [
            ([REDIS_STORAGE_CONTENTS], "redis", "REDIS"),
            ([POSTGRES_STORAGE_CONTENTS], "postgres", "RDS"),
            ([AURORA_POSTGRES_STORAGE_CONTENTS], "aurora-postgres", "AURORA"),
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
        self, fakefs, addon_file_contents, addon_type, secret_name
    ):
        fakefs.add_real_file(FIXTURES_DIR / "valid_workspace.yml", False, "copilot/.workspace")
        create_test_manifests(addon_file_contents, fakefs)

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
    def test_appconfig_ip_filter_policy_is_applied_to_each_service_by_default(self, fakefs):
        services = ["web", "web-celery"]
        fakefs.create_file(EXTENSION_CONFIG_FILENAME)
        fakefs.add_real_file(FIXTURES_DIR / "valid_workspace.yml", False, "copilot/.workspace")

        fakefs.create_file(
            "./copilot/environments/development/manifest.yml",
        )

        for service in services:
            fakefs.create_file(
                f"copilot/{service}/manifest.yml",
                contents=" ".join([yaml.dump(yaml.safe_load(WEB_SERVICE_CONTENTS))]),
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


def setup_override_files_for_environments():
    overrides_dir = Path("./copilot/environments/overrides")
    return [
        overrides_dir / "bin" / "override.ts",
        overrides_dir / ".gitignore",
        overrides_dir / "cdk.json",
        overrides_dir / "log_resource_policy.json",
        overrides_dir / "package-lock.json",
        overrides_dir / "package.json",
        overrides_dir / "README.md",
        overrides_dir / "stack.ts",
        overrides_dir / "tsconfig.json",
    ]


def create_test_manifests(addon_file_contents, fakefs):
    fakefs.create_file(
        EXTENSION_CONFIG_FILENAME,
        contents=" ".join(addon_file_contents),
    )
    fakefs.create_file(
        "copilot/web/manifest.yml",
        contents=" ".join([yaml.dump(yaml.safe_load(WEB_SERVICE_CONTENTS))]),
    )
    fakefs.create_file("copilot/environments/development/manifest.yml")
