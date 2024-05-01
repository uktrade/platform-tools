from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import mock_open
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
sso_start_url=https://uktrade.awsapps.com/start
sso_region=eu-west-2
sso_account_id = 123456789
sso_role_name = AdministratorAccess
region=eu-west-2

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
                {"accountId": "123456789012", "accountName": "Test Account 1"},
                {"accountId": "234567890123", "accountName": "Test Account 2"},
            ]
        }

        creds = {"token": "mock-aws-sso-token"}
        aws_accounts = get_aws_accounts(mock_sso_client, creds)

        # Check if the function returns the expected list of AWS accounts
        expected_accounts = [
            {"accountId": "123456789012", "accountName": "Test Account 1"},
            {"accountId": "234567890123", "accountName": "Test Account 2"},
        ]
        assert aws_accounts == expected_accounts

    def test_get_aws_accounts_empty_list(self):
        # Mock the response from the SSO client to return an empty list
        mock_sso_client = MagicMock()
        mock_sso_client.list_accounts.return_value = {"accountList": []}

        # Call the function with a mock AWS SSO token
        creds = {"token": "mock-aws-sso-token"}

        # Assert that calling the function raises a RuntimeError
        with pytest.raises(RuntimeError):
            get_aws_accounts(mock_sso_client, creds)

    @patch("dbt_platform_helper.commands.aws.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.aws.get_aws_accounts")
    @patch("boto3.session.Session")
    @patch("dbt_platform_helper.commands.aws.ConfigParser")
    @patch("builtins.open", new_callable=mock_open)
    def test_file_open_is_called(
        self,
        mock_open_call,
        mock_config_parser,
        mock_session,
        mock_aws_accounts,
        mock_get_aws_session_or_abort,
    ):
        mock_file = mock_open_call.return_value.__enter__.return_value
        mock_file.write.return_value = None

        mock_aws_accounts.return_value = [
            {"accountId": "123456789012", "accountName": "Test Account 1"},
            {"accountId": "234567890123", "accountName": "Test Account 2"},
        ]

        CliRunner().invoke(configure)

        assert mock_open_call.call_count > 0

    @patch("dbt_platform_helper.commands.aws.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.aws.get_aws_accounts")
    @patch("boto3.session.Session")
    @patch("builtins.open", new_callable=mock_open, create=True)
    def test_file_creation_and_writing(
        self, mock_open_call, mock_session, mock_aws_accounts, mock_get_aws_session_or_abort
    ):
        mock_aws_accounts.return_value = [
            {"accountId": "123456789012", "accountName": "Test Account 1"},
            {"accountId": "234567890123", "accountName": "Test Account 2"},
        ]

        expected_content = """[profile test-account-1]
sso_start_url = https://uktrade.awsapps.com/start
sso_region = eu-west-2
sso_account_id = 123456789012
sso_role_name = AdministratorAccess
region = eu-west-2

[profile test-account-2]
sso_start_url = https://uktrade.awsapps.com/start
sso_region = eu-west-2
sso_account_id = 234567890123
sso_role_name = AdministratorAccess
region = eu-west-2

"""
        CliRunner().invoke(configure)
        mock_open_call.assert_called_once_with("./aws_test_config.ini", "w")

        file_content = mock_open_call().write.call_args[0][0]
        assert file_content == expected_content

    @patch("dbt_platform_helper.commands.aws.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.aws.get_aws_accounts")
    @patch("boto3.session.Session")
    @patch("dbt_platform_helper.commands.aws.config")
    @patch("builtins.open", create=True)
    def test_configure_happy_path(
        self,
        mock_open_file,
        mock_config_parser,
        mock_session,
        mock_aws_accounts,
        mock_get_aws_session_or_abort,
    ):
        # mock_get_aws_session_or_abort.return_value = MagicMock()
        mock_aws_accounts.return_value = [
            {"accountId": "123456789012", "accountName": "Test Account 1"},
            {"accountId": "234567890123", "accountName": "Test Account 2"},
        ]

        result = CliRunner().invoke(configure)
        print(f"RESULT IS: --- {result.output}")

        mock_aws_accounts.assert_called_once()
        mock_config_parser_instance = mock_config_parser.return_value
        assert mock_config_parser_instance.write.call_count > 0
