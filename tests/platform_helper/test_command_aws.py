from click.testing import CliRunner


class TestAWSConfigureCommand:
    def test_not_logged_into_aws_exits_with_error(self):
        # with pytest.raises()
        CliRunner().invoke(configure)
