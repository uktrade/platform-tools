from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.database import copy
from dbt_platform_helper.commands.database import dump
from dbt_platform_helper.commands.database import load


@patch("dbt_platform_helper.commands.database.DatabaseCopy")
def test_command_dump_success(mock_database_copy_object):
    mock_database_copy_instance = mock_database_copy_object.return_value

    runner = CliRunner()
    result = runner.invoke(
        dump,
        [
            "--app",
            "my_app",
            "--env",
            "my_env",
            "--database",
            "my_postgres",
            "--vpc-name",
            "my_vpc",
        ],
    )

    assert result.exit_code == 0
    mock_database_copy_object.assert_called_once_with("my_app", "my_postgres")
    mock_database_copy_instance.dump.assert_called_once_with("my_env", "my_vpc")


@patch("dbt_platform_helper.commands.database.DatabaseCopy")
def test_command_load_success(mock_database_copy_object):
    mock_database_copy_instance = mock_database_copy_object.return_value
    runner = CliRunner()
    result = runner.invoke(
        load,
        [
            "--app",
            "my_app",
            "--env",
            "my_env",
            "--database",
            "my_postgres",
            "--vpc-name",
            "my_vpc",
        ],
    )

    assert result.exit_code == 0
    mock_database_copy_object.assert_called_once_with("my_app", "my_postgres")
    mock_database_copy_instance.load.assert_called_once_with("my_env", "my_vpc")


@patch("dbt_platform_helper.commands.database.DatabaseCopy")
def test_command_copy_success(mock_database_copy_object):
    mock_database_copy_instance = mock_database_copy_object.return_value
    runner = CliRunner()
    result = runner.invoke(
        copy,
        [
            "--app",
            "my_app",
            "--from",
            "my_prod_env",
            "--to",
            "my_hotfix_env",
            "--database",
            "my_postgres",
            "--from-vpc",
            "my_from_vpc",
            "--to-vpc",
            "my_to_vpc",
        ],
    )

    assert result.exit_code == 0
    mock_database_copy_object.assert_called_once_with("my_app", "my_postgres")
    mock_database_copy_instance.dump.assert_called_once_with("my_prod_env", "my_from_vpc")
    mock_database_copy_instance.load.assert_called_once_with("my_hotfix_env", "my_to_vpc")
