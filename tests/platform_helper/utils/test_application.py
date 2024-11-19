import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

import boto3
from moto import mock_aws

from dbt_platform_helper.exceptions import ApplicationNotFoundError
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import Environment
from dbt_platform_helper.utils.application import get_application_name
from dbt_platform_helper.utils.application import load_application


def test_getting_an_application_name_from_workspace(fakefs):
    fakefs.add_real_file(
        Path(__file__).parent.parent.joinpath("fixtures/valid_workspace.yml"),
        True,
        "copilot/.workspace",
    )
    assert get_application_name() == "test-app"


@patch("dbt_platform_helper.utils.application.abort_with_error", return_value=None)
def test_getting_an_application_name_when_no_workspace_file(abort_with_error, fakefs):
    get_application_name()

    abort_with_error.assert_called_with(
        "Cannot get application name. No copilot/.workspace file found"
    )


@patch("dbt_platform_helper.utils.application.get_profile_name_from_account_id", return_value="foo")
@patch("dbt_platform_helper.utils.application.get_aws_session_or_abort", return_value=boto3)
class EnvironmentTest(TestCase):
    def test_environment_session(self, get_aws_session_or_abort, get_profile_name_from_account_id):
        environment = Environment("test", "999999999", {})

        self.assertEqual(environment.name, "test")
        self.assertEqual(environment.account_id, "999999999")

        get_aws_session_or_abort.assert_not_called()
        get_profile_name_from_account_id.assert_not_called()

        self.assertEqual(environment.session, boto3)

        get_aws_session_or_abort.assert_called_with("foo")
        get_profile_name_from_account_id.assert_called_once()


@patch("dbt_platform_helper.utils.application.get_profile_name_from_account_id", return_value="foo")
@patch("dbt_platform_helper.utils.application.get_aws_session_or_abort", return_value=boto3)
class ApplicationTest(TestCase):
    def test_empty_application(self, get_aws_session_or_abort, get_profile_name_from_account_id):
        application = Application("test")

        self.assertEqual(application.name, "test")
        self.assertEqual(application.environments, {})
        self.assertEqual(str(application), "Application test with no environments")

    def test_application_with_environments(
        self, get_aws_session_or_abort, get_profile_name_from_account_id
    ):
        application = Application("test")
        environment_one = Environment("one", "111111111", {})
        environment_two = Environment("two", "222222222", {})
        application.environments["one"] = environment_one
        application.environments["two"] = environment_two

        self.assertEqual(application.name, "test")
        self.assertEqual(
            str(application), "Application test with environments one:111111111, two:222222222"
        )

    @mock_aws
    @patch("dbt_platform_helper.utils.application.get_application_name", return_value="test")
    def test_loading_an_application_with_environments(
        self, get_application_name, get_aws_session_or_abort, get_profile_name_from_account_id
    ):
        ssm_client = boto3.client("ssm")
        ssm_client.put_parameter(
            Name=f"/copilot/applications/test",
            Value=json.dumps(
                {
                    "name": "test",
                    "account": "111111111",
                }
            ),
            Type="String",
        )
        ssm_client.put_parameter(
            Name=f"/copilot/applications/test/environments/one",
            Value=json.dumps(
                {
                    "name": "one",
                    "accountID": "111111111",
                }
            ),
            Type="String",
        )
        ssm_client.put_parameter(
            Name=f"/copilot/applications/test/environments/two",
            Value=json.dumps(
                {
                    "name": "two",
                    "accountID": "222222222",
                }
            ),
            Type="String",
        )

        application = load_application()

        self.assertEqual(application.name, "test")
        self.assertEqual(
            str(application), "Application test with environments one:111111111, two:222222222"
        )
        self.assertEqual(application.environments["one"].session, boto3)
        self.assertEqual(application.environments["two"].session, boto3)

    @patch("dbt_platform_helper.utils.application.get_application_name", return_value="test")
    def test_load_application_does_not_fail_when_addons_params_are_present(
        self, get_application_name, get_aws_session_or_abort, get_profile_name_from_account_id
    ):
        """
        Note that we are mocking the session, as moto has different behaviour
        than boto3 when using the get_parameters_by_path method.

        It only brings back parameters at the same level as that path where
        boto3 will bring back nested paramaters as well.
        """
        mock_client = MagicMock(name="client-mock")
        mock_session = MagicMock(name="session-mock")
        mock_session.client.return_value = mock_client
        mock_client.get_caller_identity.return_value = {"Account": "111111111"}
        mock_client.get_parameters_by_path.side_effect = [
            {
                "Parameters": [
                    {
                        "Name": f"/copilot/applications/test/environments/one",
                        "Value": json.dumps({"name": "one", "accountID": "111111111"}),
                    },
                    {
                        "Name": f"/copilot/applications/test/environments/two/addons",
                        "Value": json.dumps(
                            {"demodjango-redis": {"type": "redis", "environments": {}}}
                        ),
                    },
                    {
                        "Name": f"/copilot/applications/test/environments/two/something/else",
                        "Value": json.dumps(
                            {"demodjango-redis": {"type": "redis", "environments": {}}}
                        ),
                    },
                ]
            },
            {
                "Parameters": [
                    {
                        "Name": "/copilot/applications/another-test/components/web",
                        "Value": '{"app": "demoddjango", "name": "web", "type": "Load Balanced Web Service"}',
                    }
                ]
            },
        ]

        application = load_application(default_session=mock_session)

        self.assertEqual(application.name, "test")
        self.assertEqual(str(application), "Application test with environments one:111111111")

    @mock_aws
    @patch("dbt_platform_helper.utils.application.get_application_name", return_value="test")
    def test_loading_an_empty_application(
        self, get_application_name, get_aws_session_or_abort, get_profile_name_from_account_id
    ):
        ssm_client = boto3.client("ssm")
        ssm_client.put_parameter(
            Name=f"/copilot/applications/test",
            Value=json.dumps(
                {
                    "name": "test",
                    "account": "111111111",
                }
            ),
            Type="String",
        )

        application = load_application()

        self.assertEqual(application.name, "test")
        self.assertEqual(str(application), "Application test with no environments")

    @mock_aws
    def test_loading_an_empty_application_passing_in_the_name_and_session(
        self, get_aws_session_or_abort, get_profile_name_from_account_id
    ):
        session = MagicMock(name="session-mock")
        client = MagicMock(name="client-mock")
        session.client.return_value = client

        client.get_caller_identity.return_value = {"Account": "abc_123"}
        client.get_parameters_by_path.side_effect = [
            {
                "Parameters": [
                    {
                        "Name": "/copilot/applications/another-test/environments/my_env",
                        "Value": '{"name": "my_env", "accountID": "abc_123"}',
                    }
                ]
            },
            {
                "Parameters": [
                    {
                        "Name": "/copilot/applications/another-test/components/web",
                        "Value": '{"app": "demoddjango", "name": "web", "type": "Load Balanced Web Service"}',
                    },
                    {
                        "Name": "/copilot/applications/another-test/components/web2",
                        "Value": '{"app": "demoddjango", "name": "web2", "type": "Load Balanced Web Service"}',
                    },
                ]
            },
        ]

        application = load_application(app="another-test", default_session=session)

        self.assertEqual(application.name, "another-test")
        self.assertEqual(len(application.environments), 1)
        self.assertEqual(application.environments["my_env"].name, "my_env")
        self.assertEqual(application.environments["my_env"].session, session)
        self.assertEqual(application.services["web"].name, "web")
        self.assertEqual(application.services["web"].kind, "Load Balanced Web Service")
        self.assertEqual(application.services["web2"].name, "web2")
        self.assertEqual(application.services["web2"].kind, "Load Balanced Web Service")

    @mock_aws
    @patch("dbt_platform_helper.utils.application.get_application_name", return_value="test")
    def test_loading_an_application_in_a_different_account(
        self, get_application_name, get_aws_session_or_abort, get_profile_name_from_account_id
    ):
        ssm_client = boto3.client("ssm")
        ssm_client.put_parameter(
            Name=f"/copilot/applications/test",
            Value=json.dumps(
                {
                    "name": "test",
                    "account": "111111111",
                }
            ),
            Type="String",
        )

        self.assertRaises(ApplicationNotFoundError, load_application, "sample")
