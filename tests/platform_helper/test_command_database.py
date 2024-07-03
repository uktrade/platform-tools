from unittest.mock import patch

import boto3
from click.testing import CliRunner
from moto import mock_aws

from dbt_platform_helper.utils.application import Application


@mock_aws
@patch(
    "dbt_platform_helper.commands.database.get_aws_session_or_abort", return_value=boto3.Session()
)
@patch("click.confirm")
def test_copy(alias_session, aws_credentials, mock_application):
    """Test that given a source and target database identifier, the copy command
    copies data from source to target database."""
    from dbt_platform_helper.commands.database import copy

    source_db = f"{mock_application.name}-development-{mock_application.name}-postgres"
    target_db = f"{mock_application.name}-staging-{mock_application.name}-postgres"

    _setup_test_databases(source_db, mock_application, "development")
    _setup_test_databases(target_db, mock_application, "staging")

    runner = CliRunner()
    result = runner.invoke(
        copy,
        [
            "--source-db",
            source_db,
            "--target-db",
            target_db,
        ],
    )

    assert f"Copying data from {source_db} to {target_db}" in result.output
    assert result.exit_code == 0


def _setup_test_databases(db_identifier: str, app: Application, env: str):
    boto3.client("rds").create_db_instance(
        DBName="main",
        DBInstanceIdentifier=db_identifier,
        DBInstanceClass="db.t3.micro",
        Engine="postgres",
        MasterUsername="postgres",
        MasterUserPassword="password",
        EngineVersion="16.2",
        Tags=[
            {"Key": "copilot-application", "Value": app.name},
            {"Key": "copilot-environment", "Value": env},
        ],
    )
