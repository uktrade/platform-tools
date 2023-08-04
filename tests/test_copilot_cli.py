from pathlib import Path

import boto3
import pytest
import yaml
from click.testing import CliRunner
from moto import mock_ssm

from commands.copilot_cli import copilot as cli
from commands.utils import SSM_PATH

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


class TestMakeAddonCommand:
    def test_exit_if_no_copilot_directory(self, fakefs):
        fakefs.create_file("addons.yml")

        result = CliRunner().invoke(cli, ["make-addons"])

        assert result.exit_code == 1
        assert (
            result.output
            == "Cannot find copilot directory. Run this command in the root of the deployment repository.\n"
        )

    def test_exit_if_no_local_copilot_services(self, fakefs):
        fakefs.create_file("addons.yml")

        fakefs.create_file("copilot/environments/development/manifest.yml")

        result = CliRunner().invoke(cli, ["make-addons"])

        assert result.exit_code == 1
        assert result.output == "No services found in ./copilot/; exiting\n"

    def test_exit_with_error_if_invalid_services(self, fakefs):
        fakefs.create_file(
            "addons.yml",
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

        result = CliRunner().invoke(cli, ["make-addons"])

        assert result.exit_code == 1
        assert result.output == "Services listed in invalid-entry.services do not exist in ./copilot/\n"

    def test_exit_with_error_if_invalid_environments(self, fakefs):
        fakefs.create_file(
            "addons.yml",
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

        result = CliRunner().invoke(cli, ["make-addons"])

        assert result.exit_code == 1
        assert result.output == "Environment keys listed in invalid-environment do not match ./copilot/environments\n"

    def test_exit_if_services_key_invalid(self, fakefs):
        """
        The services key can be set to a list of services, or '__all__' which
        denotes that it should be applied to all services.

        Any other string value results in an error.
        """

        fakefs.create_file(
            "addons.yml",
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

        result = CliRunner().invoke(cli, ["make-addons"])

        assert result.exit_code == 1
        assert result.output == "invalid-entry.services must be a list of service names or '__all__'\n"

    def test_exit_if_no_local_copilot_environments(self, fakefs):
        fakefs.create_file("addons.yml")

        fakefs.create_file("copilot/web/manifest.yml")

        result = CliRunner().invoke(cli, ["make-addons"])

        assert result.exit_code == 1
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
    def test_env_addons_parameters_file_with_different_addon_types(
        self, fakefs, addon_file_contents, addon_type
    ):
        fakefs.create_file(
            "addons.yml",
            contents=addon_file_contents,
        )
        fakefs.create_file("copilot/web/manifest.yml")
        fakefs.create_file("copilot/environments/development/manifest.yml")

        result = CliRunner().invoke(cli, ["make-addons"])

        assert result.exit_code == 0
        if addon_type == "s3":
            assert (
                "File copilot/environments/addons/addons.parameters.yml" not in result.output
            ), f"addons.parameters.yml should not be included for {addon_type}"
        else:
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
    def test_addon_instructions_with_postgres_addon_types(
        self, fakefs, addon_file_contents, addon_type, secret_name
    ):
        fakefs.create_file(
            "addons.yml",
            contents=addon_file_contents,
        )
        fakefs.create_file("copilot/web/manifest.yml")
        fakefs.create_file("copilot/environments/development/manifest.yml")

        result = CliRunner().invoke(cli, ["make-addons"])

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

    def test_appconfig_ip_filter_policy_is_applied_to_each_service_by_default(self, fakefs):
        services = ["web", "web-celery"]

        fakefs.create_file("./addons.yml")

        fakefs.create_file(
            "./copilot/environments/development/manifest.yml",
        )

        for service in services:
            fakefs.create_file(
                f"copilot/{service}/manifest.yml",
            )

        result = CliRunner().invoke(cli, ["make-addons"])

        for service in services:
            path = Path(f"copilot/{service}/addons/appconfig-ipfilter.yml")
            assert path.exists()

        assert result.exit_code == 0


@mock_ssm
def test_get_secrets():
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

    result = CliRunner().invoke(cli, ["get-env-secrets", "myapp", "myenv"])

    for name, value in secrets:
        path = SSM_PATH.format(app="myapp", env="myenv", name=name)
        line = f"{path}: {value}"

        assert line in result.output

    assert SSM_PATH.format(app="myapp", env="anotherenv", name="OTHER_ENV") not in result.output

    assert result.exit_code == 0
