from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_platform_helper.commands.aws import configure
from dbt_platform_helper.commands.aws import get_aws_accounts


class TestAWSConfigureCommand:

    @patch("dbt_platform_helper.commands.aws.get_aws_session_or_abort")
    @patch("boto3.session.Session")
    def test_get_aws_session_or_abort_is_called(self, mock_session, mock_get_aws_session_or_abort):
        CliRunner().invoke(configure)

        assert mock_get_aws_session_or_abort.call_count > 0

    @patch("dbt_platform_helper.commands.aws.get_aws_accounts", return_value=[])
    @patch("dbt_platform_helper.commands.aws.get_aws_session_or_abort")
    @patch("boto3.session.Session")
    def test_writes_aws_config_file(
        self, mock_session, mock_get_aws_session_or_abort, mock_get_aws_accounts, fakefs
    ):
        expected_output = """[default]
region=eu-west-2
sso_start_url=https://uktrade.awsapps.com/start
sso_region=eu-west-2
sso_account_id = 123456789
sso_role_name = AdministratorAccess

[profile test-account]
sso_start_url=https://uktrade.awsapps.com/start
sso_region=eu-west-2
sso_account_id = 123456789
sso_role_name = AdministratorAccess
region=eu-west-2
"""
        result = CliRunner().invoke(configure)
        assert result.exit_code == 0
        assert expected_output in Path("aws_config").read_text()

    # ///////////////////////////////////////////////////////////////////////
    @patch("dbt_platform_helper.commands.aws.get_aws_session_or_abort", return_value=None)
    @patch("boto3.session.Session")
    def test_gets_aws_account_list(self, mock_session, mock_get_aws_session_or_abort):
        mock_sso_client = MagicMock()
        mock_sso_client.list_accounts.return_value = {
            "accountList": [
                {"AccountId": "123456789012", "AccountName": "Test Account 1"},
                {"AccountId": "234567890123", "AccountName": "Test Account 2"},
            ]
        }

        creds = {"token": "mock-aws-sso-token"}
        aws_accounts = get_aws_accounts(mock_sso_client, creds)

        # Check if the function returns the expected list of AWS accounts
        expected_accounts = [
            {"AccountId": "123456789012", "AccountName": "Test Account 1"},
            {"AccountId": "234567890123", "AccountName": "Test Account 2"},
        ]
        assert aws_accounts == expected_accounts

    def test_retrieve_aws_accounts_empty_list(self):
        # Mock the response from the SSO client to return an empty list
        mock_sso_client = MagicMock()
        mock_sso_client.list_accounts.return_value = {"accountList": []}

        # Call the function with a mock AWS SSO token
        creds = {"token": "mock-aws-sso-token"}

        # Assert that calling the function raises a RuntimeError
        with pytest.raises(RuntimeError):
            get_aws_accounts(mock_sso_client, creds)
