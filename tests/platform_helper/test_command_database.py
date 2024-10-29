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
            "--from",
            "my_env",
            "--database",
            "my_postgres",
            "--from-vpc",
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
            "--to",
            "my_env",
            "--database",
            "my_postgres",
            "--to-vpc",
            "my_vpc",
        ],
    )

    assert result.exit_code == 0
    mock_database_copy_object.assert_called_once_with("my_app", "my_postgres", False)
    mock_database_copy_instance.load.assert_called_once_with("my_env", "my_vpc")


@patch("dbt_platform_helper.commands.database.DatabaseCopy")
def test_command_load_success_with_auto_approve(mock_database_copy_object):
    mock_database_copy_instance = mock_database_copy_object.return_value
    runner = CliRunner()
    result = runner.invoke(
        load,
        [
            "--app",
            "my_app",
            "--to",
            "my_env",
            "--database",
            "my_postgres",
            "--to-vpc",
            "my_vpc",
            "--auto-approve",
        ],
    )

    assert result.exit_code == 0
    mock_database_copy_object.assert_called_once_with("my_app", "my_postgres", True)
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
    mock_database_copy_object.assert_called_once_with("my_app", "my_postgres", False)
    mock_database_copy_instance.copy.assert_called_once_with(
        "my_prod_env",
        "my_hotfix_env",
        "my_from_vpc",
        "my_to_vpc",
        ("web",),
        "default",
        False,
    )


@patch("dbt_platform_helper.commands.database.DatabaseCopy")
def test_command_copy_success_with_auto_approve(mock_database_copy_object):
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
            "--auto-approve",
            "--svc",
            "other",
            "--svc",
            "service",
            "--template",
            "migration",
        ],
    )

    assert result.exit_code == 0
    mock_database_copy_object.assert_called_once_with("my_app", "my_postgres", True)
    mock_database_copy_instance.copy.assert_called_once_with(
        "my_prod_env",
        "my_hotfix_env",
        "my_from_vpc",
        "my_to_vpc",
        ("other", "service"),
        "migration",
        False,
    )


@patch("dbt_platform_helper.commands.database.DatabaseCopy")
def test_command_copy_success_with_no_maintenance_page(mock_database_copy_object):
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
            "--auto-approve",
            "--svc",
            "other",
            "--svc",
            "service",
            "--no-maintenance-page",
        ],
    )

    assert result.exit_code == 0
    mock_database_copy_object.assert_called_once_with("my_app", "my_postgres", True)
    mock_database_copy_instance.copy.assert_called_once_with(
        "my_prod_env",
        "my_hotfix_env",
        "my_from_vpc",
        "my_to_vpc",
        ("other", "service"),
        "default",
        True,
    )


@patch("dbt_platform_helper.commands.database.DatabaseCopy")
def test_command_copy_success_with_maintenance_page(mock_database_copy_object):
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
            "--auto-approve",
            "--svc",
            "other",
            "--svc",
            "service",
        ],
    )

    assert result.exit_code == 0
    mock_database_copy_object.assert_called_once_with("my_app", "my_postgres", True)
    mock_database_copy_instance.copy.assert_called_once_with(
        "my_prod_env",
        "my_hotfix_env",
        "my_from_vpc",
        "my_to_vpc",
        ("other", "service"),
        "default",
        False,
    )
