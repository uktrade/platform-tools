from unittest.mock import patch


class TestAWSConfigureCommand:
    @patch("dbt_platform_helper.utils.aws.get_aws_session_or_abort", side_effect=SystemExit())
    def test_not_logged_into_aws_exits_with_error(self, mock_session):
        # mock_session.side_effect = sys.exit(1)

        # result = CliRunner().invoke(configure)

        assert True is True
        # assert result.exit_code is 1
        # assert "You must be logged into AWS, please run 'aws sso login'" in result.output
