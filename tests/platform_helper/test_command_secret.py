import os

# import shutil
# from http import HTTPStatus
# from pathlib import Path
# from unittest.mock import MagicMock
# from unittest.mock import Mock
# from unittest.mock import call
# from unittest.mock import patch
#
# import boto3
# import pytest
from click.testing import CliRunner

# from cloudfoundry_client.common_objects import JsonObject
# from freezegun import freeze_time
# from moto import mock_ssm
from moto import mock_sts

# from oauth2_client.credentials_manager import OAuthError
# from schema import SchemaError
#
from dbt_platform_helper.commands.secrets import copy

# from dbt_platform_helper.commands.bootstrap import get_paas_env_vars
# from dbt_platform_helper.commands.bootstrap import make_config
# from dbt_platform_helper.commands.bootstrap import migrate_secrets
# from dbt_platform_helper.utils.aws import set_ssm_param
# from dbt_platform_helper.utils.files import load_and_validate_config
# from dbt_platform_helper.utils.validation import BOOTSTRAP_SCHEMA
# from tests.platform_helper.conftest import FIXTURES_DIR
# from tests.platform_helper.conftest import TEST_APP_DIR
#
#
# class MockEntity(JsonObject):
#     def spaces(self):
#         space = MockEntity(entity={"name": "trade-space"})
#         return [space]
#
#     def apps(self):
#         app = MockEntity(
#             entity={"name": "test-service", "environment_json": {"TEST_VAR": "TEST_VAR"}}
#         )
#         return [app]
#
#


@mock_sts
def test_copy_secrets_without_new_environment_directory(alias_session, aws_credentials, tmp_path):
    # switch_to_tmp_dir_and_copy_config_file(tmp_path, FIXTURES_DIR / "valid_bootstrap_config.yml")
    os.mkdir(f"{tmp_path}/copilot")

    runner = CliRunner()

    # Todo: Understand implications of not running make_config
    # runner.invoke(make_config)

    result = runner.invoke(
        copy,
        ["development", "newenv", "--project-profile", "foo"],
    )

    assert result.exit_code == 1
    assert """Target environment manifest for "newenv" does not exist.""" in result.output


# @pytest.mark.parametrize("bootstrap_exists", [True, False])
# @patch("dbt_platform_helper.commands.bootstrap.get_ssm_secrets")
# @patch("dbt_platform_helper.commands.bootstrap.set_ssm_param")
# @mock_ssm
# @mock_sts
# def test_copy_secrets(
#     set_ssm_param, get_ssm_secrets, bootstrap_exists, alias_session, aws_credentials, tmp_path
# ):
#     get_ssm_secrets.return_value = [
#         (
#             "/copilot/test-application/development/secrets/ALLOWED_HOSTS",
#             "test-application.development.dbt",
#         ),
#         ("/copilot/test-application/development/secrets/TEST_SECRET", "test value"),
#     ]
#
#     runner = CliRunner()
#     setup_newenv_environment(tmp_path, runner, bootstrap_exists)
#
#     result = runner.invoke(copy_secrets, ["development", "newenv", "--project-profile", "foo"])
#
#     set_ssm_param.assert_has_calls(
#         [
#             call(
#                 "test-application",
#                 "newenv",
#                 "/copilot/test-application/newenv/secrets/ALLOWED_HOSTS",
#                 "test-application.development.dbt",
#                 False,
#                 False,
#                 "Copied from development environment.",
#             ),
#             call(
#                 "test-application",
#                 "newenv",
#                 "/copilot/test-application/newenv/secrets/TEST_SECRET",
#                 "test value",
#                 False,
#                 False,
#                 "Copied from development environment.",
#             ),
#         ]
#     )
#     assert "/copilot/test-application/newenv/secrets/ALLOWED_HOSTS" in result.output
#     assert "/copilot/test-application/newenv/secrets/TEST_SECRET" in result.output
#
#
# @pytest.mark.parametrize("bootstrap_exists", [True, False])
# @patch("dbt_platform_helper.commands.bootstrap.get_ssm_secrets")
# @patch("dbt_platform_helper.commands.bootstrap.set_ssm_param")
# @mock_ssm
# @mock_sts
# def test_copy_secrets_skips_aws_secrets(
#     set_ssm_param, get_ssm_secrets, bootstrap_exists, alias_session, aws_credentials, tmp_path
# ):
#     get_ssm_secrets.return_value = [
#         ("/copilot/test-application/development/secrets/GOOD_SECRET", "good value"),
#         ("/copilot/test-application/development/secrets/AWS_BAD_SECRET", "bad value"),
#     ]
#
#     runner = CliRunner()
#     setup_newenv_environment(tmp_path, runner, bootstrap_exists)
#
#     result = runner.invoke(copy_secrets, ["development", "newenv", "--project-profile", "foo"])
#
#     set_ssm_param.assert_called_once()
#     set_ssm_param.assert_has_calls(
#         [
#             call(
#                 "test-application",
#                 "newenv",
#                 "/copilot/test-application/newenv/secrets/GOOD_SECRET",
#                 "good value",
#                 False,
#                 False,
#                 "Copied from development environment.",
#             ),
#         ]
#     )
#     assert "/copilot/test-application/newenv/secrets/GOOD_SECRET" in result.output
#     assert "/copilot/test-application/newenv/secrets/AWS_BAD_SECRET" not in result.output
#
#
# @pytest.mark.parametrize("bootstrap_exists", [True, False])
# @patch("dbt_platform_helper.commands.bootstrap.get_ssm_secrets")
# @patch("dbt_platform_helper.commands.bootstrap.set_ssm_param")
# @mock_ssm
# @mock_sts
# def test_copy_secrets_with_existing_secret(
#     set_ssm_param, get_ssm_secrets, bootstrap_exists, alias_session, aws_credentials, tmp_path
# ):
#     set_ssm_param.side_effect = alias_session.client("ssm").exceptions.ParameterAlreadyExists(
#         {
#             "Error": {
#                 "Code": "ParameterAlreadyExists",
#                 "Message": "The parameter already exists. To overwrite this value, set the overwrite option in the request to true.",
#             },
#         },
#         "PutParameter",
#     )
#
#     get_ssm_secrets.return_value = [
#         ("/copilot/test-application/development/secrets/TEST_SECRET", "test value"),
#     ]
#
#     runner = CliRunner()
#     setup_newenv_environment(tmp_path, runner, bootstrap_exists)
#
#     result = runner.invoke(copy_secrets, ["development", "newenv", "--project-profile", "foo"])
#
#     assert (
#         """The "TEST_SECRET" parameter already exists for the "newenv" environment."""
#         in result.output
#     )


# def setup_newenv_environment(tmp_path, runner, bootstrap_exists):
#     switch_to_tmp_dir_and_copy_config_file(tmp_path, TEST_APP_DIR / "bootstrap.yml")
#     copilot_dir = tmp_path / "copilot"
#     copilot_dir.mkdir()
#
#     with open(copilot_dir / ".workspace", "w") as fh:
#         fh.write("application: test-application\n")
#
#     runner.invoke(make_config)
#
#     if not bootstrap_exists:
#         Path("bootstrap.yml").unlink()
#
#     my_file = FIXTURES_DIR / "newenv_environment_manifest.yml"
#     envdir = copilot_dir / "environments/newenv"
#     envdir.mkdir(parents=True)
#     to_file = envdir / "manifest.yml"
#     shutil.copy(my_file, to_file)
#
#
# def switch_to_tmp_dir_and_copy_config_file(tmp_path, bootstrap_config_file):
#     os.chdir(tmp_path)
#     shutil.copy(bootstrap_config_file, "bootstrap.yml")
#
#
# def get_parameter(secret_name):
#     return (
#         boto3.session.Session()
#         .client("ssm")
#         .get_parameter(Name=f"/copilot/test-app/test/secrets/{secret_name}")
#     )
#
#
# def assert_secret_exists_with_value(secret_name, secret_value):
#     response = get_parameter(secret_name)
#     assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
#     assert response["Parameter"]["Value"] == f"kms:alias/aws/ssm:{secret_value}"
#
#
# def assert_secret_does_not_exist(secret_name):
#     try:
#         response = get_parameter(f"{secret_name}")
#     except Exception as exception:
#         assert exception.response["Error"]["Code"] == "ParameterNotFound"
#         return
#
#     assert response["ResponseMetadata"]["HTTPStatusCode"] != 200
