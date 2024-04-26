from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.aws import configure


class TestAWSConfigureCommand:
    @patch(
        "dbt_platform_helper.utils.aws.get_aws_session_or_abort",
        return_value=None,
        side_effect=SystemExit(),
    )
    def test_not_logged_into_aws_exits_with_error(self, mock_get_aws_session_or_abort):

        result = CliRunner().invoke(configure)

        assert result.exit_code is 1
        assert (
            "The SSO session associated with this profile has expired or is otherwise invalid"
            in result.output
        )

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
