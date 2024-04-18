import os
import shutil
from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

import boto3
import pytest
from click.testing import CliRunner
from cloudfoundry_client.common_objects import JsonObject
from freezegun import freeze_time
from moto import mock_aws
from oauth2_client.credentials_manager import OAuthError
from schema import SchemaError

from dbt_platform_helper.commands.bootstrap import copy_secrets
from dbt_platform_helper.commands.bootstrap import get_paas_env_vars
from dbt_platform_helper.commands.bootstrap import make_config
from dbt_platform_helper.commands.bootstrap import migrate_secrets
from dbt_platform_helper.utils.aws import set_ssm_param
from dbt_platform_helper.utils.files import load_and_validate_config
from dbt_platform_helper.utils.validation import BOOTSTRAP_SCHEMA
from tests.platform_helper.conftest import FIXTURES_DIR
from tests.platform_helper.conftest import TEST_APP_DIR


class MockEntity(JsonObject):
    def spaces(self):
        space = MockEntity(entity={"name": "trade-space"})
        return [space]

    def apps(self):
        app = MockEntity(
            entity={"name": "test-service", "environment_json": {"TEST_VAR": "TEST_VAR"}}
        )
        return [app]


def test_get_pass_env_vars():
    """Test that, given a CloudFoundryClient instance and an app's path string,
    get_paas_env_vars returns a dict of environment variables."""
    client = Mock()

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


@pytest.mark.xdist_group(name="fileaccess")
def test_load_and_validate_config_invalid_file():
    """Test that, given the path to an invalid yaml file,
    load_and_validate_config raises a SchemaError with specific field errors."""

    path = FIXTURES_DIR / "invalid_bootstrap_config.yml"

    with pytest.raises(SchemaError) as err:
        load_and_validate_config(path, BOOTSTRAP_SCHEMA)

    assert (
        err.value.args[0]
        == "Key 'environments' error:\n[{'test': None, 'certificate_arns': ['ACM-ARN-FOR-test.landan.cloudapps.digital']}, {'production': None, 'certificate_arns': ['ACM-ARN-FOR-test.landan.cloudapps.digital']}] should be instance of 'dict'"
    )


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch(
    "dbt_platform_helper.utils.versioning.get_app_versions",
    new=Mock(return_value=[(1, 0, 0), (1, 0, 0)]),
)
def test_make_config(tmp_path):
    """Test that make_config generates the expected directories and file
    contents."""

    test_environment_manifest = Path(FIXTURES_DIR, "test_environment_manifest.yml").read_text()
    production_environment_manifest = Path(
        FIXTURES_DIR, "production_environment_manifest.yml"
    ).read_text()
    test_public_service_manifest = Path(
        FIXTURES_DIR, "test_public_service_manifest.yml"
    ).read_text()
    test_backend_service_manifest = Path(
        FIXTURES_DIR, "test_backend_service_manifest.yml"
    ).read_text()

    assert not (tmp_path / "copilot").exists()
    switch_to_tmp_dir_and_copy_config_file(tmp_path, FIXTURES_DIR / "valid_bootstrap_config.yml")
    os.mkdir(f"{tmp_path}/copilot")

    result = CliRunner().invoke(make_config)

    assert (
        "GitHub documentation: https://github.com/uktrade/platform-documentation/blob/main/gov-pass-to-copilot-migration"
        in result.output
    )

    assert (tmp_path / ".platform-helper-version").exists()

    with open(str(tmp_path / ".platform-helper-version")) as platform_helper_version_file:
        assert platform_helper_version_file.read() == "1.0.0"

    assert (tmp_path / "copilot").exists()

    with open(str(tmp_path / "copilot/.workspace")) as workspace:
        assert workspace.read() == "application: test-app"

    with open(str(tmp_path / "copilot/environments/test/manifest.yml")) as test:
        assert test.read() == test_environment_manifest

    with open(str(tmp_path / "copilot/environments/production/manifest.yml")) as production:
        assert production.read() == production_environment_manifest

    with open(str(tmp_path / "copilot/test-public-service/manifest.yml")) as service:
        assert service.read() == test_public_service_manifest

    assert os.path.exists(str(tmp_path / "copilot/test-public-service/addons"))

    with open(str(tmp_path / "copilot/test-backend-service/manifest.yml")) as service:
        assert service.read() == test_backend_service_manifest

    assert os.path.exists(str(tmp_path / "copilot/test-backend-service/addons"))


@mock_aws
@patch("dbt_platform_helper.utils.cloudfoundry.CloudFoundryClient")
@pytest.mark.xdist_group(name="fileaccess")
def test_migrate_secrets_login_failure(mock_client, alias_session, aws_credentials, tmp_path):
    """Test that when login fails, a helpful message is printed and the command
    aborts."""
    exception = OAuthError(
        HTTPStatus(401),
        "invalid_token",
        "Invalid refresh token expired at Wed Aug 30 06:00:43 UTC 2023",
    )
    mock_client.build_from_cf_config.side_effect = exception

    result = CliRunner().invoke(
        migrate_secrets,
        ["--project-profile", "foo", "--env", "staging", "--svc", "test-service"],
    )

    assert result.exit_code == 1
    assert f"Could not connect to Cloud Foundry: {str(exception)}" in result.output
    assert "Please log in with: cf login" in result.output


@mock_aws
@patch("dbt_platform_helper.utils.cloudfoundry.CloudFoundryClient")
def test_migrate_secrets_env_not_in_config(client, alias_session, aws_credentials, tmp_path):
    """Test that, given a config file path and an environment not found in that
    file, migrate_secrets outputs the expected error message."""

    switch_to_tmp_dir_and_copy_config_file(tmp_path, FIXTURES_DIR / "valid_bootstrap_config.yml")

    result = CliRunner().invoke(
        migrate_secrets,
        ["--project-profile", "foo", "--env", "staging", "--svc", "test-service"],
    )

    assert f"staging is not an environment in bootstrap.yml" in result.output


@mock_aws
@patch("dbt_platform_helper.utils.cloudfoundry.CloudFoundryClient")
def test_migrate_secrets_service_not_in_config(client, alias_session, aws_credentials, tmp_path):
    """Test that, given a config file path and a secret not found in that file,
    migrate_secrets outputs the expected error message."""

    switch_to_tmp_dir_and_copy_config_file(tmp_path, FIXTURES_DIR / "valid_bootstrap_config.yml")

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
@mock_aws
@patch("dbt_platform_helper.commands.bootstrap.get_paas_env_vars")
@patch("dbt_platform_helper.utils.cloudfoundry.CloudFoundryClient")
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
    switch_to_tmp_dir_and_copy_config_file(tmp_path, FIXTURES_DIR / "valid_bootstrap_config.yml")

    result = CliRunner().invoke(
        migrate_secrets,
        ["--project-profile", "foo", "--env", "test", "--svc", "test-public-service"],
    )

    assert (
        ">>> migrating secrets for service: test-public-service; environment: test" in result.output
    )
    assert "Created" in result.output

    assert_secret_exists_with_value("TEST_SECRET", param_value)


@mock_aws
@patch("dbt_platform_helper.commands.bootstrap.get_paas_env_vars", return_value={})
@patch("dbt_platform_helper.utils.cloudfoundry.CloudFoundryClient")
def test_migrate_secrets_param_already_exists(
    client, get_paas_env_vars, alias_session, aws_credentials, tmp_path
):
    """Test that, where a secret already exists in aws ssm and overwrite flag
    isn't set, migrate_secrets doesn't update it."""

    set_ssm_param(
        "test-app",
        "test",
        "/copilot/test-app/test/secrets/TEST_SECRET",
        "NOT_FOUND",
        False,
        False,
    )
    switch_to_tmp_dir_and_copy_config_file(tmp_path, FIXTURES_DIR / "valid_bootstrap_config.yml")

    result = CliRunner().invoke(
        migrate_secrets,
        ["--project-profile", "foo", "--env", "test", "--svc", "test-public-service"],
    )

    assert "NOT overwritten" in result.output

    response = get_parameter("TEST_SECRET")

    assert response["Parameter"]["Version"] == 1


@mock_aws
@patch("dbt_platform_helper.commands.bootstrap.get_paas_env_vars", return_value={})
@patch("dbt_platform_helper.utils.cloudfoundry.CloudFoundryClient")
def test_migrate_secrets_overwrite(
    client, get_paas_env_vars, alias_session, aws_credentials, tmp_path
):
    """Test that, where a secret already exists in aws ssm and overwrite flag is
    set, migrate_secrets updates it."""

    set_ssm_param(
        "test-app",
        "test",
        "/copilot/test-app/test/secrets/TEST_SECRET",
        "NOT_FOUND",
        False,
        False,
    )
    switch_to_tmp_dir_and_copy_config_file(tmp_path, FIXTURES_DIR / "valid_bootstrap_config.yml")

    result = CliRunner().invoke(
        migrate_secrets,
        [
            "--project-profile",
            "foo",
            "--env",
            "test",
            "--svc",
            "test-public-service",
            "--overwrite",
        ],
    )

    assert "Overwritten" in result.output
    assert "NOT overwritten" not in result.output

    response = get_parameter("TEST_SECRET")

    assert response["Parameter"]["Version"] == 2


@mock_aws
@patch("dbt_platform_helper.commands.bootstrap.get_paas_env_vars", return_value={})
@patch("dbt_platform_helper.utils.cloudfoundry.CloudFoundryClient")
def test_migrate_secrets_dry_run(
    client, get_paas_env_vars, alias_session, aws_credentials, tmp_path
):
    """Test that, when dry-run flag is passed, migrate_secrets does not create a
    secret."""

    switch_to_tmp_dir_and_copy_config_file(tmp_path, FIXTURES_DIR / "valid_bootstrap_config.yml")

    result = CliRunner().invoke(
        migrate_secrets,
        ["--project-profile", "foo", "--env", "test", "--svc", "test-public-service", "--dry-run"],
    )

    assert (
        "/copilot/test-app/test/secrets/TEST_SECRET not created because `--dry-run` flag was included."
        in result.output
    )

    client = boto3.session.Session().client("ssm")

    with pytest.raises(client.exceptions.ParameterNotFound):
        client.get_parameter(Name="/copilot/test-app/test/secrets/TEST_SECRET")


@mock_aws
@patch("dbt_platform_helper.commands.bootstrap.get_paas_env_vars")
@patch("dbt_platform_helper.utils.cloudfoundry.CloudFoundryClient")
def test_migrate_secrets_skips_aws_secrets(
    client,
    get_paas_env_vars_mock,
    alias_session,
    aws_credentials,
    tmp_path,
):
    """Test that, where a secret's name begins with "AWS_", it is not
    migrated."""

    good_secret_name = "TEST_SECRET"
    good_secret_value = "good value"
    bad_secret_name = "AWS_BAD_SECRET"
    bad_secret_value = "bad value"

    get_paas_env_vars_mock.return_value = {
        good_secret_name: good_secret_value,
        bad_secret_name: bad_secret_value,
    }
    switch_to_tmp_dir_and_copy_config_file(tmp_path, FIXTURES_DIR / "valid_bootstrap_config.yml")

    CliRunner().invoke(
        migrate_secrets,
        ["--project-profile", "foo", "--env", "test", "--svc", "test-public-service"],
    )

    assert_secret_exists_with_value(good_secret_name, good_secret_value)
    assert_secret_does_not_exist(bad_secret_name)


def test_migrate_secrets_profile_not_configured(clear_session_cache, tmp_path):
    switch_to_tmp_dir_and_copy_config_file(tmp_path, FIXTURES_DIR / "valid_bootstrap_config.yml")

    result = CliRunner().invoke(
        migrate_secrets,
        ["--project-profile", "foo", "--env", "test", "--svc", "test-service", "--dry-run"],
    )

    assert """AWS profile "foo" is not configured.""" in result.output


def test_copy_secrets_profile_not_configured(clear_session_cache, tmp_path):
    switch_to_tmp_dir_and_copy_config_file(tmp_path, FIXTURES_DIR / "valid_bootstrap_config.yml")

    result = CliRunner().invoke(
        copy_secrets,
        ["development", "newenv", "--project-profile", "foo"],
    )

    assert """AWS profile "foo" is not configured.""" in result.output


@mock_aws
def test_copy_secrets_without_new_environment_directory(alias_session, aws_credentials, tmp_path):
    switch_to_tmp_dir_and_copy_config_file(tmp_path, FIXTURES_DIR / "valid_bootstrap_config.yml")
    os.mkdir(f"{tmp_path}/copilot")

    runner = CliRunner()

    runner.invoke(make_config)

    result = runner.invoke(
        copy_secrets,
        ["development", "newenv", "--project-profile", "foo"],
    )

    assert result.exit_code == 1
    assert """Target environment manifest for "newenv" does not exist.""" in result.output


@pytest.mark.parametrize("bootstrap_exists", [True, False])
@patch("dbt_platform_helper.commands.bootstrap.get_ssm_secrets")
@patch("dbt_platform_helper.commands.bootstrap.set_ssm_param")
@mock_aws
def test_copy_secrets(
    set_ssm_param, get_ssm_secrets, bootstrap_exists, alias_session, aws_credentials, tmp_path
):
    get_ssm_secrets.return_value = [
        (
            "/copilot/test-application/development/secrets/ALLOWED_HOSTS",
            "test-application.development.dbt",
        ),
        ("/copilot/test-application/development/secrets/TEST_SECRET", "test value"),
    ]

    runner = CliRunner()
    setup_newenv_environment(tmp_path, runner, bootstrap_exists)

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


@pytest.mark.parametrize("bootstrap_exists", [True, False])
@patch("dbt_platform_helper.commands.bootstrap.get_ssm_secrets")
@patch("dbt_platform_helper.commands.bootstrap.set_ssm_param")
@mock_aws
def test_copy_secrets_skips_aws_secrets(
    set_ssm_param, get_ssm_secrets, bootstrap_exists, alias_session, aws_credentials, tmp_path
):
    get_ssm_secrets.return_value = [
        ("/copilot/test-application/development/secrets/GOOD_SECRET", "good value"),
        ("/copilot/test-application/development/secrets/AWS_BAD_SECRET", "bad value"),
    ]

    runner = CliRunner()
    setup_newenv_environment(tmp_path, runner, bootstrap_exists)

    result = runner.invoke(copy_secrets, ["development", "newenv", "--project-profile", "foo"])

    set_ssm_param.assert_called_once()
    set_ssm_param.assert_has_calls(
        [
            call(
                "test-application",
                "newenv",
                "/copilot/test-application/newenv/secrets/GOOD_SECRET",
                "good value",
                False,
                False,
                "Copied from development environment.",
            ),
        ]
    )
    assert "/copilot/test-application/newenv/secrets/GOOD_SECRET" in result.output
    assert "/copilot/test-application/newenv/secrets/AWS_BAD_SECRET" not in result.output


@pytest.mark.parametrize("bootstrap_exists", [True, False])
@patch("dbt_platform_helper.commands.bootstrap.get_ssm_secrets")
@patch("dbt_platform_helper.commands.bootstrap.set_ssm_param")
@mock_aws
def test_copy_secrets_with_existing_secret(
    set_ssm_param, get_ssm_secrets, bootstrap_exists, alias_session, aws_credentials, tmp_path
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
    setup_newenv_environment(tmp_path, runner, bootstrap_exists)

    result = runner.invoke(copy_secrets, ["development", "newenv", "--project-profile", "foo"])

    assert (
        """The "TEST_SECRET" parameter already exists for the "newenv" environment."""
        in result.output
    )


def setup_newenv_environment(tmp_path, runner, bootstrap_exists):
    switch_to_tmp_dir_and_copy_config_file(tmp_path, TEST_APP_DIR / "bootstrap.yml")
    copilot_dir = tmp_path / "copilot"
    copilot_dir.mkdir()

    with open(copilot_dir / ".workspace", "w") as fh:
        fh.write("application: test-application\n")

    runner.invoke(make_config)

    if not bootstrap_exists:
        Path("bootstrap.yml").unlink()

    my_file = FIXTURES_DIR / "newenv_environment_manifest.yml"
    envdir = copilot_dir / "environments/newenv"
    envdir.mkdir(parents=True)
    to_file = envdir / "manifest.yml"
    shutil.copy(my_file, to_file)


def switch_to_tmp_dir_and_copy_config_file(tmp_path, bootstrap_config_file):
    os.chdir(tmp_path)
    shutil.copy(bootstrap_config_file, "bootstrap.yml")


def get_parameter(secret_name):
    return (
        boto3.session.Session()
        .client("ssm")
        .get_parameter(Name=f"/copilot/test-app/test/secrets/{secret_name}")
    )


def assert_secret_exists_with_value(secret_name, secret_value):
    response = get_parameter(secret_name)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["Parameter"]["Value"] == f"kms:alias/aws/ssm:{secret_value}"


def assert_secret_does_not_exist(secret_name):
    try:
        response = get_parameter(f"{secret_name}")
    except Exception as exception:
        assert exception.response["Error"]["Code"] == "ParameterNotFound"
        return

    assert response["ResponseMetadata"]["HTTPStatusCode"] != 200
