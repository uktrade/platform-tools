from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import boto3
import pytest
import yaml
from click.testing import CliRunner
from cloudfoundry_client.common_objects import JsonObject
from moto import mock_ssm
from schema import SchemaError

from commands.bootstrap_cli import get_paas_env_vars
from commands.bootstrap_cli import instructions
from commands.bootstrap_cli import load_and_validate_config
from commands.bootstrap_cli import make_config
from commands.bootstrap_cli import migrate_secrets
from commands.utils import set_ssm_param
from tests import bootstrap_strings


class MockEntity(JsonObject):
    def spaces(self):
        space = MockEntity(entity={"name": "trade-space"})
        return [space]

    def apps(self):
        app = MockEntity(entity={"name": "test-service", "environment_json": {"TEST_VAR": "TEST_VAR"}})
        return [app]


@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_get_pass_env_vars(client):
    """Test that, given a CloudFoundryClient instance and an app's path string,
    get_paas_env_vars returns a dict of environment variables."""

    org = MockEntity(entity={"name": "dit-staging"})
    client.v2.organizations = [org]
    paas = "dit-staging/trade-space/test-service"
    env_vars = get_paas_env_vars(client, paas)

    assert env_vars == {"TEST_VAR": "TEST_VAR"}


def test_get_paas_env_vars_exception():
    """Test that get_pass_env_vars raises expected Exception error message when
    no application is found."""

    client = MagicMock()
    paas = "dit-blah/trade-space/trade-app"

    with pytest.raises(Exception) as err:
        get_paas_env_vars(client, paas)

    assert err.value.args[0] == f"Application {paas} not found"


def test_load_and_validate_config_valid_file():
    """Test that, given the path to a valid yaml file, load_and_validate_config
    returns the loaded yaml unmodified."""

    path = Path(__file__).parent.resolve() / "test_config.yml"
    validated = load_and_validate_config(path)

    with open(path, "r") as fd:
        conf = yaml.safe_load(fd)

    assert validated == conf


def test_load_and_validate_config_invalid_file():
    """Test that, given the path to an invalid yaml file,
    load_and_validate_config raises a SchemaError with specific field errors."""

    path = Path(__file__).parent.resolve() / "invalid_test_config.yml"

    with pytest.raises(SchemaError) as err:
        load_and_validate_config(path)

    assert (
        err.value.args[0]
        == "Key 'environments' error:\n[{'test': None, 'certificate_arns': ['ACM-ARN-FOR-test.landan.cloudapps.digital']}, {'production': None, 'certificate_arns': ['ACM-ARN-FOR-test.landan.cloudapps.digital']}] should be instance of 'dict'"
    )


def test_make_config(tmp_path):
    """Test that, given a config file path and an output path, make_config
    generates the expected directories and file contents."""

    config_file_path = Path(__file__).parent.resolve() / "test_config.yml"
    runner = CliRunner()
    result = runner.invoke(make_config, [str(config_file_path), str(tmp_path)])

    assert (
        "GitHub documentation: https://github.com/uktrade/platform-documentation/blob/main/gov-pass-to-copiltot-migration"
        in result.output
    )
    assert (tmp_path / "copilot").exists()

    with open(str(tmp_path / "copilot/.workspace")) as workspace:
        assert workspace.read() == "application: test-app"

    with open(str(tmp_path / "copilot/environments/test/manifest.yml")) as test:
        assert test.read() == bootstrap_strings.TEST_MANIFEST

    with open(str(tmp_path / "copilot/environments/production/manifest.yml")) as production:
        assert production.read() == bootstrap_strings.PRODUCTION_MANIFEST

    with open(str(tmp_path / "copilot/test-service/manifest.yml")) as service:
        assert service.read() == bootstrap_strings.SERVICE_MANIFEST


@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_env_not_in_config(client):
    """Test that, given a config file path and an environment not found in that
    file, migrate_secrets outputs the expected error message."""

    config_file_path = Path(__file__).parent.resolve() / "test_config.yml"
    runner = CliRunner()
    result = runner.invoke(migrate_secrets, [str(config_file_path), "--env", "staging", "--svc", "test-service"])
    path = str(Path(__file__).parent.resolve() / "test_config.yml")
    assert f"staging is not an environment in {path}" in result.output


@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_service_not_in_config(client):
    """Test that, given a config file path and a secret not found in that file,
    migrate_secrets outputs the expected error message."""

    config_file_path = Path(__file__).parent.resolve() / "test_config.yml"
    runner = CliRunner()
    result = runner.invoke(migrate_secrets, [str(config_file_path), "--env", "test", "--svc", "blah"])
    path = str(Path(__file__).parent.resolve() / "test_config.yml")
    assert f"blah is not a service in {path}" in result.output


@pytest.mark.parametrize(
    "env_vars,param_value",
    [({}, "NOT FOUND"), ({"TEST_SECRET": None}, "EMPTY"), ({"TEST_SECRET": "TEST_SECRET"}, "TEST_SECRET")],
)
@mock_ssm
@patch("commands.bootstrap_cli.get_paas_env_vars")
@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_param_doesnt_exist(client, get_paas_env_vars, env_vars, param_value):
    """Test that, where a secret doesn't already exist in aws ssm,
    migrate_secrets creates it."""

    get_paas_env_vars.return_value = env_vars
    config_file_path = Path(__file__).parent.resolve() / "test_config.yml"
    runner = CliRunner()
    result = runner.invoke(migrate_secrets, [str(config_file_path), "--env", "test", "--svc", "test-service"])

    assert ">>> migrating secrets for service: test-service; environment: test" in result.output
    assert "Created" in result.output

    client = boto3.session.Session().client("ssm")
    response = client.get_parameter(Name="/copilot/test-app/test/secrets/TEST_SECRET")

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["Parameter"]["Value"] == f"kms:alias/aws/ssm:{param_value}"


@mock_ssm
@patch("commands.bootstrap_cli.get_paas_env_vars", return_value={})
@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_param_already_exists(client, get_paas_env_vars):
    """Test that, where a secret already exists in aws ssm and overwrite flag
    isn't set, migrate_secrets doesn't update it."""

    set_ssm_param("test-app", "test", "/copilot/test-app/test/secrets/TEST_SECRET", "NOT_FOUND", False, False)
    config_file_path = Path(__file__).parent.resolve() / "test_config.yml"
    runner = CliRunner()
    result = runner.invoke(migrate_secrets, [str(config_file_path), "--env", "test", "--svc", "test-service"])

    assert "NOT overwritten" in result.output

    client = boto3.session.Session().client("ssm")
    response = client.get_parameter(Name="/copilot/test-app/test/secrets/TEST_SECRET")

    assert response["Parameter"]["Version"] == 1


@mock_ssm
@patch("commands.bootstrap_cli.get_paas_env_vars", return_value={})
@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_overwrite(client, get_paas_env_vars):
    """Test that, where a secret already exists in aws ssm and overwrite flag is
    set, migrate_secrets updates it."""

    set_ssm_param("test-app", "test", "/copilot/test-app/test/secrets/TEST_SECRET", "NOT_FOUND", False, False)
    config_file_path = Path(__file__).parent.resolve() / "test_config.yml"
    runner = CliRunner()
    result = runner.invoke(
        migrate_secrets,
        [str(config_file_path), "--env", "test", "--svc", "test-service", "--overwrite"],
    )

    assert "Overwritten" in result.output
    assert "NOT overwritten" not in result.output

    client = boto3.session.Session().client("ssm")
    response = client.get_parameter(Name="/copilot/test-app/test/secrets/TEST_SECRET")

    assert response["Parameter"]["Version"] == 2


@mock_ssm
@patch("commands.bootstrap_cli.get_paas_env_vars", return_value={})
@patch("commands.bootstrap_cli.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_dry_run(client, get_paas_env_vars):
    """Test that, when dry-run flag is passed, migrate_secrets does not create a
    secret."""

    config_file_path = Path(__file__).parent.resolve() / "test_config.yml"
    runner = CliRunner()
    result = runner.invoke(
        migrate_secrets,
        [str(config_file_path), "--env", "test", "--svc", "test-service", "--dry-run"],
    )

    assert (
        "/copilot/test-app/test/secrets/TEST_SECRET not created because `--dry-run` flag was included."
        in result.output
    )

    client = boto3.session.Session().client("ssm")

    with pytest.raises(client.exceptions.ParameterNotFound):
        client.get_parameter(Name="/copilot/test-app/test/secrets/TEST_SECRET")


def test_instructions():
    """Test that, given the path to a config file, instructions generates output
    for specific services and environments."""

    config_file_path = Path(__file__).parent.resolve() / "test_config.yml"
    runner = CliRunner()
    result = runner.invoke(instructions, [str(config_file_path)])

    assert result.output == bootstrap_strings.INSTRUCTIONS
