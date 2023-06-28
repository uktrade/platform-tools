from pathlib import Path

import boto3
import yaml
from click.testing import CliRunner
from moto import mock_ssm

from commands.copilot_cli import copilot as cli
from commands.utils import SSM_PATH


class TestMakeStorageCommand:
    def test_exit_if_no_copilot_directory(self, fakefs):
        fakefs.create_file("storage.yml")

        runner = CliRunner()

        result = runner.invoke(cli, ["make-storage"])

        assert result.exit_code == 1
        assert (
            result.output
            == "Cannot find copilot directory. Run this command in the root of the deployment repository.\n"
        )

    def test_exit_if_no_local_copilot_services(self, fakefs):
        fakefs.create_file("storage.yml")

        fakefs.create_file("copilot/environments/development/manifest.yml")

        runner = CliRunner()

        result = runner.invoke(cli, ["make-storage"])

        assert result.exit_code == 1
        assert result.output == "No services found in ./copilot/; exiting\n"

    def test_exit_with_error_if_invalid_services(self, fakefs):
        fakefs.create_file(
            "storage.yml",
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

        runner = CliRunner()

        result = runner.invoke(cli, ["make-storage"])

        assert result.exit_code == 1
        assert result.output == "Services listed in invalid-entry.services do not exist in ./copilot/\n"

    def test_exit_with_error_if_invalid_environments(self, fakefs):
        fakefs.create_file(
            "storage.yml",
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

        runner = CliRunner()

        result = runner.invoke(cli, ["make-storage"])

        assert result.exit_code == 1
        assert result.output == "Environment keys listed in invalid-environment do not match ./copilot/environments\n"

    def test_exit_if_services_key_invalid(self, fakefs):
        """
        The services key can be set to a list of services, or '__all__' which
        denotes that it should be applied to all services.

        Any other string value results in an error.
        """

        fakefs.create_file(
            "storage.yml",
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

        runner = CliRunner()

        result = runner.invoke(cli, ["make-storage"])

        assert result.exit_code == 1
        assert result.output == "invalid-entry.services must be a list of service names or '__all__'\n"

    def test_exit_if_no_local_copilot_environments(self, fakefs):
        fakefs.create_file("storage.yml")

        fakefs.create_file("copilot/web/manifest.yml")

        runner = CliRunner()

        result = runner.invoke(cli, ["make-storage"])

        assert result.exit_code == 1
        assert result.output == "No environments found in ./copilot/environments; exiting\n"

    def test_ip_filter_policy_is_applied_to_each_service_by_default(self, fakefs):
        services = ["web", "web-celery"]

        fakefs.create_file("./storage.yml")

        fakefs.create_file(
            "./copilot/environments/development/manifest.yml",
        )

        for service in services:
            fakefs.create_file(
                f"copilot/{service}/manifest.yml",
            )

        runner = CliRunner()

        result = runner.invoke(cli, ["make-storage"])

        for service in services:
            path = Path(f"copilot/{service}/addons/ip-filter.yml")
            assert path.exists()

            with open(path, "r") as fd:
                s3_policy = yaml.safe_load(fd)

            assert s3_policy["Mappings"]["ipFilterBucketNameMap"] == {"development": {"BucketName": "ipfilter-config"}}

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

    runner = CliRunner()

    result = runner.invoke(cli, ["get-env-secrets", "myapp", "myenv"])

    for name, value in secrets:
        path = SSM_PATH.format(app="myapp", env="myenv", name=name)
        line = f"{path}: {value}"

        assert line in result.output

    assert SSM_PATH.format(app="myapp", env="anotherenv", name="OTHER_ENV") not in result.output

    assert result.exit_code == 0
