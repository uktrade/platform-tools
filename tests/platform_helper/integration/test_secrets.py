import re
from unittest.mock import MagicMock
from unittest.mock import call

import pytest
from botocore.exceptions import ClientError

from dbt_platform_helper.constants import MANAGED_BY_PLATFORM
from dbt_platform_helper.domain.secrets import Secrets
from dbt_platform_helper.platform_exception import PlatformException


class CreateMock:
    def __init__(self, user_policy_type="none", create_existing_params="none"):
        self.create_existing_params = create_existing_params
        self.user_policy_type = user_policy_type
        self.mocks = None

    def setup(self, mock_application):

        self.load_application_mock = MagicMock()
        self._create_sessions(mock_application)
        self.load_application_mock.return_value = mock_application
        self._create_existing_params()

        self.io_mock = MagicMock()
        self.io_mock.input.side_effect = ["1", "2", "3", "4"]

        return dict(
            load_application=self.load_application_mock,
            io=self.io_mock,
            parameter_store_provider=self.parameter_store_provider_mock,
        )

    def _create_existing_params(self):
        self.parameter_store_provider_mock = MagicMock()

        self.parameter_store_mock = MagicMock()

        if self.create_existing_params == "exists":
            self.parameter_store_mock.get_ssm_parameter_by_name.side_effect = [
                {"Name": "doesntmatter"},
                {"Name": "doesntmatter1"},
                {"Name": "doesntmatter2"},
                {"Name": "doesntmatter3"},
            ]
        elif self.create_existing_params == "unexpected":
            self.parameter_store_mock.get_ssm_parameter_by_name.side_effect = [
                ClientError(
                    {"Error": {"Code": "Unexpected", "Message": "Simulated failure"}},
                    "GetParameter",
                ),
            ]
        else:
            self.parameter_store_mock.get_ssm_parameter_by_name.side_effect = [
                ClientError(
                    {"Error": {"Code": "ParameterNotFound", "Message": "Simulated failure"}},
                    "GetParameter",
                ),
                ClientError(
                    {"Error": {"Code": "ParameterNotFound", "Message": "Simulated failure"}},
                    "GetParameter",
                ),
                ClientError(
                    {"Error": {"Code": "ParameterNotFound", "Message": "Simulated failure"}},
                    "GetParameter",
                ),
                ClientError(
                    {"Error": {"Code": "ParameterNotFound", "Message": "Simulated failure"}},
                    "GetParameter",
                ),
            ]
        self.parameter_store_provider_mock.return_value = self.parameter_store_mock

    def _create_sessions(self, application):
        mocks = {}
        for env, env_object in application.environments.items():
            mock_session = MagicMock(name=f"{env}-session-mock")
            mock_sts_client = MagicMock(name=f"{env}-sts-client-mock")
            mock_sts_client.get_caller_identity.return_value = {
                "Arn": f"arn:sts:assume-role/{env}/something"
            }

            mock_iam_client = MagicMock(name=f"{env}-iam-client-mock")
            mock_ssm_client = MagicMock(name=f"{env}-ssm-client-mock")

            if self.user_policy_type == "admin":
                mock_iam_client.list_attached_role_policies.return_value = {
                    "AttachedPolicies": [{"PolicyName": "AdministratorAccess"}]
                }
            else:
                mock_iam_client.list_attached_role_policies.return_value = {"AttachedPolicies": []}

            if self.user_policy_type == "inline":
                mock_iam_client.list_role_policies.return_value = {"PolicyNames": ["inline"]}
                mock_iam_client.get_role_policy.return_value = {
                    "PolicyDocument": {"Statement": [{"Action": ["acm:*", "ssm:*"]}]}
                }
            else:
                mock_iam_client.list_role_policies.return_value = {"PolicyNames": []}

            mocks[env] = {
                "session": mock_session,
            }

            mock_session.client.side_effect = self.__make_client_side_effect(
                mock_sts_client, mock_iam_client, mock_ssm_client
            )
            application.environments[env].sessions[
                application.environments[env].account_id
            ] = mock_session
        self.mocks = mocks

    def __make_client_side_effect(self, mock_sts_client, mock_iam_client, mock_ssm_client):
        def client_side_effect(service):
            return {
                "sts": mock_sts_client,
                "iam": mock_iam_client,
                "ssm": mock_ssm_client,
            }.get(service)

        return client_side_effect


@pytest.mark.parametrize(
    "input_args, policies, params_exist",
    [
        ({"app_name": "test-application", "name": "secret", "overwrite": False}, "admin", "none"),
        ({"app_name": "test-application", "name": "secret", "overwrite": True}, "inline", "exists"),
        ({"app_name": "test-application", "name": "secret", "overwrite": False}, "inline", "none"),
    ],
)
def test_create(mock_application, input_args, policies, params_exist):

    mock = CreateMock(user_policy_type=policies, create_existing_params=params_exist)
    input_mocks = mock.setup(mock_application)
    secrets = Secrets(**input_mocks)

    secrets.create(**input_args)

    i = 1
    put_parameter_calls = []
    info_calls = []
    input_calls = []
    for env, mocked in mock.mocks.items():
        mocked["session"].client("sts").get_caller_identity.assert_called_once()
        mocked["session"].client("iam").list_attached_role_policies.assert_called_with(RoleName=env)

        if policies == "inline":
            mocked["session"].client("iam").list_role_policies.assert_called_with(RoleName=env)
            mocked["session"].client("iam").get_role_policy.assert_called_with(
                RoleName=env, PolicyName="inline"
            )

        called_with = dict(
            Name=f"/platform/test-application/{env}/secrets/SECRET",
            Value=str(i),
            Overwrite=False,
            Type="SecureString",
            Tags=[
                {"Key": "application", "Value": "test-application"},
                {"Key": "environment", "Value": env},
                {"Key": "managed-by", "Value": MANAGED_BY_PLATFORM},
            ],
        )

        if input_args["overwrite"]:
            called_with["Overwrite"] = True
            del called_with["Tags"]

        put_parameter_calls.append(call(called_with))
        info_calls.append(
            call(f"Creating AWS SSM secret /platform/test-application/{env}/secrets/SECRET")
        )
        input_calls.append(
            call(
                f"Please enter value for secret 'SECRET' in environment '{env}'",
                hide_input=True,
            )
        )

        i += 1
    mock.io_mock.info.assert_has_calls(info_calls)
    mock.io_mock.input.assert_has_calls(input_calls)
    mock.parameter_store_mock.put_parameter.assert_has_calls(put_parameter_calls)


def test_create_no_access(mock_application):

    mock = CreateMock()
    input_mocks = mock.setup(mock_application)
    secrets = Secrets(**input_mocks)

    with pytest.raises(
        PlatformException,
        match="""You do not have SSM write access to the following AWS accounts: '000000000', '111111111', '222222222', '333333333'""",
    ):
        secrets.create("test-application", "secret", False)


def test_create_exception_parameter_found(mock_application):

    mock = CreateMock(user_policy_type="admin", create_existing_params="exists")
    input_mocks = mock.setup(mock_application)
    secrets = Secrets(**input_mocks)

    with pytest.raises(
        PlatformException,
        match="""SSM parameter 'SECRET' already exists for the following environments: 'development', 'staging', 'production', 'test'.""",
    ):
        secrets.create("test-application", "secret", False)


def test_create_exception_unexpected(mock_application):

    mock = CreateMock(user_policy_type="admin", create_existing_params="unexpected")
    input_mocks = mock.setup(mock_application)
    secrets = Secrets(**input_mocks)

    with pytest.raises(
        PlatformException,
        match=re.escape(
            """An error occurred (Unexpected) when calling the GetParameter operation: Simulated failure"""
        ),
    ):
        secrets.create("test-application", "secret", False)
