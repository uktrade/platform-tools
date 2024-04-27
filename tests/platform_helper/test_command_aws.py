from unittest.mock import patch

import botocore
import pytest

# from botocore.exceptions import UnauthorizedException
from dbt_platform_helper.utils.aws import get_aws_session_or_abort


class TestAWSConfigureCommand:

    # @patch(
    #     "dbt_platform_helper.utils.aws.get_aws_session_or_abort",
    #     return_value=None,
    #     side_effect=SystemExit(),
    # )
    # @patch('boto3.session.Session', return_value=None)
    # def test_not_logged_into_aws_exits_with_error(self, mock_get_aws_session_or_abort, mock_session):
    #
    #     result = CliRunner().invoke(configure)
    #     print(f"LOOK HERE: {result.output}")
    #     assert result.exit_code is 1
    #     assert (
    #         "The SSO session associated with this profile has expired or is otherwise invalid"
    #         in result.output
    #     )

    @patch("click.secho")
    def test_get_aws_session_or_abort_with_misconfigured_profile(self, mock_secho):
        misconfigured_profile = "nonexistent_profile"
        expected_error_message = f"""AWS profile "{misconfigured_profile}" is not configured."""

        with patch("boto3.session.Session") as mock_session:
            mock_session.side_effect = botocore.exceptions.ProfileNotFound(
                profile=misconfigured_profile
            )

            with pytest.raises(SystemExit) as exc_info:
                get_aws_session_or_abort(aws_profile=misconfigured_profile)

            assert exc_info.value.code == 1
            assert mock_secho.call_count > 0
            assert mock_secho.call_args[0][0] == expected_error_message

    @patch("click.secho")
    def test_get_aws_session_or_abort_with_invalid_credentials(self, mock_secho):
        aws_profile = "existing_profile"
        expected_error_message = f"Credentials are NOT valid.  \nPlease login with: aws sso login --profile {aws_profile}"

        with patch("boto3.session.Session") as mock_session:
            with patch(
                "dbt_platform_helper.utils.aws.get_account_details"
            ) as mock_get_account_details:
                mock_get_account_details.side_effect = botocore.exceptions.SSOTokenLoadError(
                    error_msg=expected_error_message
                )

                with pytest.raises(SystemExit) as exc_info:
                    get_aws_session_or_abort(aws_profile=aws_profile)

                assert exc_info.value.code == 1
                assert mock_secho.call_count > 0
                assert mock_secho.call_args[0][0] == expected_error_message

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
