from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_platform_helper.commands.config import aws
from dbt_platform_helper.commands.config import migrate
from dbt_platform_helper.commands.config import validate
from dbt_platform_helper.platform_exception import PlatformException


@patch("dbt_platform_helper.commands.config.Config")
def test_command_validate_success(mock_config_domain):
    mock_config_domain_instance = mock_config_domain.return_value

    runner = CliRunner()
    result = runner.invoke(validate)

    assert result.exit_code == 0
    mock_config_domain_instance.validate.assert_called()
    mock_config_domain.assert_called()


@patch("dbt_platform_helper.commands.config.Config")
def test_command_validate_raises_platform_exception(mock_config_domain):
    mock_config_domain_instance = mock_config_domain.return_value
    mock_config_domain_instance.validate.side_effect = PlatformException("i've failed")

    runner = CliRunner()
    result = runner.invoke(validate)

    assert result.exit_code == 1
    mock_config_domain.assert_called()


@pytest.mark.parametrize(
    "cli_args, called_with",
    [
        ([], "~/.aws/config"),
        (["--file-path", "path"], "path"),
        (["-fp", "short-path"], "short-path"),
    ],
)
@patch("dbt_platform_helper.commands.config.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.config.Config")
@patch("dbt_platform_helper.commands.config.SSOAuthProvider")
def test_command_aws_success(
    mock_auth_provider, mock_config_domain, mock_session, cli_args, called_with
):
    mock_config_domain_instance = mock_config_domain.return_value

    runner = CliRunner()
    result = runner.invoke(aws, cli_args)
    mock_config_domain_instance.generate_aws.assert_called_with(called_with)

    mock_auth_provider.assert_called_with(mock_session())
    mock_config_domain.assert_called_with(sso=mock_auth_provider())
    assert result.exit_code == 0


@patch("dbt_platform_helper.commands.config.get_aws_session_or_abort")
@patch("dbt_platform_helper.commands.config.Config")
def test_command_aws_raises_platform_exception(mock_config_domain, mock_session):
    mock_config_domain_instance = mock_config_domain.return_value
    mock_config_domain_instance.generate_aws.side_effect = PlatformException("i've failed")

    runner = CliRunner()
    result = runner.invoke(aws)

    assert result.exit_code == 1


@patch("dbt_platform_helper.commands.config.Config")
def test_command_migrate(mock_config_domain):
    runner = CliRunner()
    result = runner.invoke(migrate)

    assert result.exit_code == 0
    mock_config_domain.return_value.migrate.assert_called_once()


@patch("dbt_platform_helper.commands.config.ClickIOProvider")
@patch("dbt_platform_helper.commands.config.Config")
def test_command_migrate_platform_errors_cause_abort_with_error_message(
    mock_config_domain, mock_io
):
    mock_config_domain.return_value.migrate.side_effect = PlatformException("Some weird error")
    mock_io.return_value.abort_with_error.side_effect = SystemExit(1)

    runner = CliRunner()
    result = runner.invoke(migrate)

    assert result.exit_code == 1
    mock_io.return_value.abort_with_error.assert_called_once_with("Some weird error")
