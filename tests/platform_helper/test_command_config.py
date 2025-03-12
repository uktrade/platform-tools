from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_platform_helper.commands.config import aws
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
    "cli_args",
    [[], ["--file-path", "path"], ["-fp", "short-path"]],
)
@patch("dbt_platform_helper.commands.config.Config")
def test_command_aws_success(mock_config_domain, cli_args):
    mock_config_domain_instance = mock_config_domain.return_value

    runner = CliRunner()
    result = runner.invoke(aws, cli_args)
    # TODO check generate_aws called with

    assert result.exit_code == 0
    mock_config_domain_instance.assert_called()
    mock_config_domain.assert_called()


@patch("dbt_platform_helper.commands.config.Config")
def test_command_aws_raises_platform_exception(mock_config_domain):
    mock_config_domain_instance = mock_config_domain.return_value
    mock_config_domain_instance.generate_aws.side_effect = PlatformException("i've failed")

    runner = CliRunner()
    result = runner.invoke(aws)

    assert result.exit_code == 1
