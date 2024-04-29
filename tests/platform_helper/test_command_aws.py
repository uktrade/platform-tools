from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.aws import configure


class TestAWSConfigureCommand:
    @patch("dbt_platform_helper.commands.aws.get_aws_session_or_abort")
    @patch("boto3.session.Session")
    def test_get_aws_session_or_abort_is_called1(self, mock_session, mock_get_aws_session_or_abort):
        result = CliRunner().invoke(configure)
        assert result.exit_code == 0
        assert mock_get_aws_session_or_abort.call_count > 0

    # test_writes_aws_config_file
    # Should use fake filesystem
    # Be mocked to have suitable response from sso_client.list_accounts etc.
    # Write file like...
    # [default]
    # region=eu-west-2
    # sso_start_url=https://uktrade.awsapps.com/start
    # sso_region=eu-west-2
    # sso_account_id = 123456789
    # sso_role_name = AdministratorAccess
    #
    # [profile test-account]
    # sso_start_url=https://uktrade.awsapps.com/start
    # sso_region=eu-west-2
    # sso_account_id = 123456789
    # sso_role_name = AdministratorAccess
    # region=eu-west-2
