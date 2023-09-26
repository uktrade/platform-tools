import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

import boto3
import pytest
import yaml
from click.testing import CliRunner
from cloudfoundry_client.common_objects import JsonObject
from freezegun import freeze_time
from moto import mock_ssm
from moto import mock_sts
from schema import SchemaError

from dbt_copilot_helper.commands.bootstrap import copy_secrets
from dbt_copilot_helper.commands.bootstrap import get_paas_env_vars
from dbt_copilot_helper.commands.bootstrap import load_and_validate_config
from dbt_copilot_helper.commands.bootstrap import make_config
from dbt_copilot_helper.commands.bootstrap import migrate_secrets
from dbt_copilot_helper.utils.aws import set_ssm_param
from tests.conftest import BASE_DIR
from tests.conftest import FIXTURES_DIR


class MockEntity(JsonObject):
    def spaces(self):
        space = MockEntity(entity={"name": "trade-space"})
        return [space]

    def apps(self):
        app = MockEntity(
            entity={"name": "test-service", "environment_json": {"TEST_VAR": "TEST_VAR"}}
        )
        return [app]


@patch("dbt_copilot_helper.commands.bootstrap.CloudFoundryClient", return_value=MagicMock)
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


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
def test_make_config(tmp_path):
    """Test that make_config generates the expected directories and file
    contents."""

    test_environment_manifest = Path(FIXTURES_DIR, "test_environment_manifest.yml").read_text()
    production_environment_manifest = Path(
        FIXTURES_DIR, "production_environment_manifest.yml"
    ).read_text()
    test_service_manifest = Path(FIXTURES_DIR, "test_service_manifest.yml").read_text()

    switch_to_tmp_dir_and_copy_config_file(tmp_path, "test_config.yml")
    os.mkdir(f"{tmp_path}/copilot")

    result = CliRunner().invoke(make_config)

    assert (
        "GitHub documentation: https://github.com/uktrade/platform-documentation/blob/main/gov-pass-to-copilot-migration"
        in result.output
    )

    assert (tmp_path / "copilot").exists()

    with open(str(tmp_path / "copilot/.workspace")) as workspace:
        assert workspace.read() == "application: test-app"

    with open(str(tmp_path / "copilot/environments/test/manifest.yml")) as test:
        assert test.read() == test_environment_manifest

    with open(str(tmp_path / "copilot/environments/production/manifest.yml")) as production:
        assert production.read() == production_environment_manifest

    with open(str(tmp_path / "copilot/test-service/manifest.yml")) as service:
        assert service.read() == test_service_manifest


@mock_sts
@patch("dbt_copilot_helper.commands.bootstrap.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_env_not_in_config(client, alias_session, aws_credentials, tmp_path):
    """Test that, given a config file path and an environment not found in that
    file, migrate_secrets outputs the expected error message."""

    switch_to_tmp_dir_and_copy_config_file(tmp_path, "test_config.yml")

    result = CliRunner().invoke(
        migrate_secrets,
        ["--project-profile", "foo", "--env", "staging", "--svc", "test-service"],
    )

    assert f"staging is not an environment in bootstrap.yml" in result.output


@mock_sts
@patch("dbt_copilot_helper.commands.bootstrap.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_service_not_in_config(client, alias_session, aws_credentials, tmp_path):
    """Test that, given a config file path and a secret not found in that file,
    migrate_secrets outputs the expected error message."""

    switch_to_tmp_dir_and_copy_config_file(tmp_path, "test_config.yml")

    result = CliRunner().invoke(
        migrate_secrets,
        ["--project-profile", "foo", "--env", "test", "--svc", "blah"],
    )

    assert f"blah is not a service in bootstrap.yml" in result.output


@pytest.mark.parametrize(
    "env_vars,param_value",
    [
        ({}, "NOT FOUND"),
        ({"TEST_SECRET": None}, "EMPTY"),
        ({"TEST_SECRET": "TEST_SECRET"}, "TEST_SECRET"),
    ],
)
@mock_ssm
@mock_sts
@patch("dbt_copilot_helper.commands.bootstrap.get_paas_env_vars")
@patch("dbt_copilot_helper.commands.bootstrap.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_param_doesnt_exist(
    client,
    get_paas_env_vars,
    env_vars,
    param_value,
    alias_session,
    aws_credentials,
    tmp_path,
):
    """Test that, where a secret doesn't already exist in aws ssm,
    migrate_secrets creates it."""

    get_paas_env_vars.return_value = env_vars
    switch_to_tmp_dir_and_copy_config_file(tmp_path, "test_config.yml")

    result = CliRunner().invoke(
        migrate_secrets,
        ["--project-profile", "foo", "--env", "test", "--svc", "test-service"],
    )

    assert ">>> migrating secrets for service: test-service; environment: test" in result.output
    assert "Created" in result.output

    client = boto3.session.Session().client("ssm")
    response = client.get_parameter(Name="/copilot/test-app/test/secrets/TEST_SECRET")

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["Parameter"]["Value"] == f"kms:alias/aws/ssm:{param_value}"


@mock_ssm
@mock_sts
@patch("dbt_copilot_helper.commands.bootstrap.get_paas_env_vars", return_value={})
@patch("dbt_copilot_helper.commands.bootstrap.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_param_already_exists(
    client, get_paas_env_vars, alias_session, aws_credentials, tmp_path
):
    """Test that, where a secret already exists in aws ssm and overwrite flag
    isn't set, migrate_secrets doesn't update it."""

    set_ssm_param(
        "test-app", "test", "/copilot/test-app/test/secrets/TEST_SECRET", "NOT_FOUND", False, False
    )
    switch_to_tmp_dir_and_copy_config_file(tmp_path, "test_config.yml")

    result = CliRunner().invoke(
        migrate_secrets,
        ["--project-profile", "foo", "--env", "test", "--svc", "test-service"],
    )

    assert "NOT overwritten" in result.output

    client = boto3.client("ssm")
    response = client.get_parameter(Name="/copilot/test-app/test/secrets/TEST_SECRET")

    assert response["Parameter"]["Version"] == 1


@mock_ssm
@mock_sts
@patch("dbt_copilot_helper.commands.bootstrap.get_paas_env_vars", return_value={})
@patch("dbt_copilot_helper.commands.bootstrap.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_overwrite(
    client, get_paas_env_vars, alias_session, aws_credentials, tmp_path
):
    """Test that, where a secret already exists in aws ssm and overwrite flag is
    set, migrate_secrets updates it."""

    set_ssm_param(
        "test-app", "test", "/copilot/test-app/test/secrets/TEST_SECRET", "NOT_FOUND", False, False
    )
    switch_to_tmp_dir_and_copy_config_file(tmp_path, "test_config.yml")

    result = CliRunner().invoke(
        migrate_secrets,
        ["--project-profile", "foo", "--env", "test", "--svc", "test-service", "--overwrite"],
    )

    assert "Overwritten" in result.output
    assert "NOT overwritten" not in result.output

    client = boto3.session.Session().client("ssm")
    response = client.get_parameter(Name="/copilot/test-app/test/secrets/TEST_SECRET")

    assert response["Parameter"]["Version"] == 2


@mock_ssm
@mock_sts
@patch("dbt_copilot_helper.commands.bootstrap.get_paas_env_vars", return_value={})
@patch("dbt_copilot_helper.commands.bootstrap.CloudFoundryClient", return_value=MagicMock)
def test_migrate_secrets_dry_run(
    client, get_paas_env_vars, alias_session, aws_credentials, tmp_path
):
    """Test that, when dry-run flag is passed, migrate_secrets does not create a
    secret."""

    switch_to_tmp_dir_and_copy_config_file(tmp_path, "test_config.yml")

    result = CliRunner().invoke(
        migrate_secrets,
        ["--project-profile", "foo", "--env", "test", "--svc", "test-service", "--dry-run"],
    )

    assert (
        "/copilot/test-app/test/secrets/TEST_SECRET not created because `--dry-run` flag was included."
        in result.output
    )

    client = boto3.session.Session().client("ssm")

    with pytest.raises(client.exceptions.ParameterNotFound):
        client.get_parameter(Name="/copilot/test-app/test/secrets/TEST_SECRET")


def test_migrate_secrets_profile_not_configured(tmp_path):
    switch_to_tmp_dir_and_copy_config_file(tmp_path, "test_config.yml")

    result = CliRunner().invoke(
        migrate_secrets,
        ["--project-profile", "foo", "--env", "test", "--svc", "test-service", "--dry-run"],
    )

    assert """AWS profile "foo" is not configured.""" in result.output


def test_copy_secrets_profile_not_configured(tmp_path):
    switch_to_tmp_dir_and_copy_config_file(tmp_path, "test_config.yml")

    result = CliRunner().invoke(
        copy_secrets,
        ["development", "newenv", "--project-profile", "foo"],
    )

    assert """AWS profile "foo" is not configured.""" in result.output


@mock_sts
def test_copy_secrets_without_new_environment_directory(alias_session, aws_credentials, tmp_path):
    switch_to_tmp_dir_and_copy_config_file(tmp_path, "test_config.yml")
    os.mkdir(f"{tmp_path}/copilot")

    runner = CliRunner()

    runner.invoke(make_config)

    result = runner.invoke(
        copy_secrets,
        ["development", "newenv", "--project-profile", "foo"],
    )

    assert result.exit_code == 1
    assert """Target environment manifest for "newenv" does not exist.""" in result.output


@patch("dbt_copilot_helper.commands.bootstrap.get_ssm_secrets")
@patch("dbt_copilot_helper.commands.bootstrap.set_ssm_param")
@mock_ssm
@mock_sts
def test_copy_secrets(set_ssm_param, get_ssm_secrets, alias_session, aws_credentials, tmp_path):
    get_ssm_secrets.return_value = [
        (
            "/copilot/test-application/development/secrets/ALLOWED_HOSTS",
            "test-application.development.dbt",
        ),
        ("/copilot/test-application/development/secrets/TEST_SECRET", "test value"),
    ]

    runner = CliRunner()
    setup_newenv_environment(tmp_path, runner)

    result = runner.invoke(copy_secrets, ["development", "newenv", "--project-profile", "foo"])

    set_ssm_param.assert_has_calls(
        [
            call(
                "test-application",
                "newenv",
                "/copilot/test-application/newenv/secrets/ALLOWED_HOSTS",
                "test-application.development.dbt",
                False,
                False,
                "Copied from development environment.",
            ),
            call(
                "test-application",
                "newenv",
                "/copilot/test-application/newenv/secrets/TEST_SECRET",
                "test value",
                False,
                False,
                "Copied from development environment.",
            ),
        ]
    )
    assert "/copilot/test-application/newenv/secrets/ALLOWED_HOSTS" in result.output
    assert "/copilot/test-application/newenv/secrets/TEST_SECRET" in result.output


@patch("dbt_copilot_helper.commands.bootstrap.get_ssm_secrets")
@patch("dbt_copilot_helper.commands.bootstrap.set_ssm_param")
@mock_ssm
@mock_sts
def test_copy_secrets_with_existing_secret(
    set_ssm_param, get_ssm_secrets, alias_session, aws_credentials, tmp_path
):
    set_ssm_param.side_effect = alias_session.client("ssm").exceptions.ParameterAlreadyExists(
        {
            "Error": {
                "Code": "ParameterAlreadyExists",
                "Message": "The parameter already exists. To overwrite this value, set the overwrite option in the request to true.",
            },
        },
        "PutParameter",
    )

    get_ssm_secrets.return_value = [
        ("/copilot/test-application/development/secrets/TEST_SECRET", "test value"),
    ]

    runner = CliRunner()
    setup_newenv_environment(tmp_path, runner)

    result = runner.invoke(copy_secrets, ["development", "newenv", "--project-profile", "foo"])

    assert (
        """The "TEST_SECRET" parameter already exists for the "newenv" environment."""
        in result.output
    )


def setup_newenv_environment(tmp_path, runner):
    switch_to_tmp_dir_and_copy_config_file(tmp_path, "test-application-deploy/bootstrap.yml")
    os.mkdir(f"{tmp_path}/copilot")

    runner.invoke(make_config)

    my_file = Path(FIXTURES_DIR, "newenv_environment_manifest.yml")
    os.mkdir(f"{tmp_path}/copilot/environments/newenv")
    to_file = Path(tmp_path / "copilot/environments/newenv/manifest.yml")
    shutil.copy(my_file, to_file)


def switch_to_tmp_dir_and_copy_config_file(tmp_path, valid_config_file):
    os.chdir(tmp_path)
    shutil.copy(f"{BASE_DIR}/tests/{valid_config_file}", "bootstrap.yml")
