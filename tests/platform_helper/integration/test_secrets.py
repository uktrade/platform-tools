import re
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import call

import pytest
from botocore.exceptions import ClientError

from dbt_platform_helper.constants import MANAGED_BY_PLATFORM
from dbt_platform_helper.domain.secrets import Secrets
from dbt_platform_helper.platform_exception import PlatformException


class AWSTestFixtures:

    @staticmethod
    def get_parameter_response(name, value):
        return {
            "Name": name,
            "Type": "SecureString",
            "Value": value,
            "ARN": f"arn:::parameter/{name}",
            "DataType": "text",
            "Version": 1,
        }

    @staticmethod
    def get_parameter_by_path_response(
        secrets, env, platform="platform", application="test-application"
    ):
        return {
            "Parameters": [
                AWSTestFixtures.get_parameter_response(
                    f"/{platform}/{application}/{env}/secrets/{secret.upper()}", secret
                )
                for secret in secrets
            ],
            "NextMarker": "string",
        }

    @staticmethod
    def list_tags_for_resource_response(
        env, application="test-application", platform="platform", managed_by="DBT Platform"
    ):
        if platform == "platform":
            return {
                "TagList": [
                    {"Key": "application", "Value": application},
                    {"Key": "environment", "Value": env},
                    {"Key": "managed-by", "Value": managed_by},
                ]
            }
        else:
            return {
                "TagList": [
                    {"Key": "copilot-application", "Value": application},
                    {"Key": "copilot-environment", "Value": env},
                ]
            }

    @staticmethod
    def client_error_response(function, code="Unexpected", message="Simulated failure"):
        return ClientError(
            {"Error": {"Code": code, "Message": message}},
            function,
        )

    @staticmethod
    def get_parameter_not_found_error_response():
        return AWSTestFixtures.client_error_response("GetParameter", code="ParameterNotFound")

    @staticmethod
    def put_parameter_already_exists_error_response():
        return AWSTestFixtures.client_error_response("PutParameter", code="ParameterAlreadyExists")

    @staticmethod
    def simulate_principal_policy_response(action="ssm:PutParameter", decision="allowed"):
        return {
            "EvaluationResults": [
                {
                    "EvalActionName": action,
                    "EvalResourceName": "*",
                    "EvalDecision": decision,
                    "MatchedStatements": [],
                }
            ],
        }

    @staticmethod
    def put_parameter_called_with(
        env,
        value,
        overwrite=False,
        application="test-application",
        description="",
        secret="SECRET",
        platform="platform",
        tags=[],
    ):
        called_with = dict(
            Name=f"/{platform}/test-application/{env}/secrets/{secret.upper()}",
            Value=str(value),
            Overwrite=False,
            Type="SecureString",
            Tags=tags
            + [
                {"Key": "application", "Value": application},
                {"Key": "environment", "Value": env},
                {"Key": "managed-by", "Value": MANAGED_BY_PLATFORM},
            ],
        )

        if description:
            called_with["Description"] = description
        if overwrite:
            called_with["Overwrite"] = True
            del called_with["Tags"]

        return called_with

    @staticmethod
    def put_parameter_copied_called_with(platform, source, target, secret, tags=[]):
        tags = [{"Key": "copied-from", "Value": source}] + tags
        description = f"Copied from {source} environment."
        return AWSTestFixtures.put_parameter_called_with(
            target,
            value=secret,
            secret=secret,
            platform=platform,
            description=description,
            tags=tags,
        )

    @staticmethod
    def simulate_principal_policy_called_with(account_id, role_name, actions=["ssm:PutParameter"]):
        return dict(
            PolicySourceArn=f"arn:aws:iam::{account_id}:role/aws-reserved/sso.amazonaws.com/eu-west-2/{role_name}",
            ActionNames=actions,
            ContextEntries=[
                {
                    "ContextKeyName": "aws:RequestedRegion",
                    "ContextKeyValues": [
                        "eu-west-2",
                    ],
                    "ContextKeyType": "string",
                }
            ],
        )

    @staticmethod
    def get_ssm_parameters_by_path_called_with(
        env,
        application="test-application",
        platform="platform",
    ):
        return dict(
            Path=f"/{platform}/{application}/{env}/secrets",
            Recursive=True,
            WithDecryption=True,
        )


class AWSMocks:
    def __init__(
        self,
        has_access={"all": True},
        put_parameter_unexpected=False,
        create_existing_params="none",
    ):
        self.create_existing_params = create_existing_params
        self.has_access = has_access
        self.mocks = None
        self.put_parameter_unexpected = put_parameter_unexpected

    def setup_create(self, mock_application):

        self.application = mock_application
        self.load_application_mock = MagicMock()
        self._create_sessions()
        self.load_application_mock.return_value = mock_application

        self.io_mock = MagicMock()
        self.io_mock.input.side_effect = ["1", "2", "3", "4", "5"]

        return dict(
            load_application=self.load_application_mock,
            io=self.io_mock,
        )

    def _create_sessions(self):
        mocks = {}
        for env, env_object in self.application.environments.items():
            mock_session = MagicMock(name=f"{env}-session-mock")
            mock_sts_client = MagicMock(name=f"{env}-sts-client-mock")
            mock_sts_client.get_caller_identity.return_value = {
                "Arn": f"arn:sts:assume-role/{env}/something"
            }

            mock_iam_client = MagicMock(name=f"{env}-iam-client-mock")
            mock_ssm_client = MagicMock(name=f"{env}-ssm-client-mock")

            if self.has_access["all"]:
                mock_iam_client.simulate_principal_policy.return_value = (
                    AWSTestFixtures.simulate_principal_policy_response()
                )
            else:
                mock_iam_client.simulate_principal_policy.return_value = (
                    AWSTestFixtures.simulate_principal_policy_response(decision="implicitDeny")
                )

            # will overwrite but works in line with code
            mocks[self.application.environments[env].account_id] = {
                "session": mock_session,
                "env": env,
            }

            if self.create_existing_params == "exists":
                mock_ssm_client.get_parameter.return_value = {"Parameter": {"Name": "doesntmatter"}}
            elif self.create_existing_params == "unexpected":
                mock_ssm_client.get_parameter.side_effect = AWSTestFixtures.client_error_response(
                    "GetParameter"
                )
            else:
                mock_ssm_client.get_parameter.side_effect = (
                    AWSTestFixtures.get_parameter_not_found_error_response()
                )

            mock_session.client.side_effect = self.__make_client_side_effect(
                mock_sts_client, mock_iam_client, mock_ssm_client
            )

            self.application.environments[env].sessions[
                self.application.environments[env].account_id
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

    def _create_parameters_by_path_paginator(self, env):
        paginator = Mock()
        paginator.paginate.side_effect = [
            [
                AWSTestFixtures.get_parameter_by_path_response(
                    secrets=["secret1", "secret2"], env=env, platform="copilot"
                ),
            ],
            [
                AWSTestFixtures.get_parameter_by_path_response(
                    secrets=["secret_exists", "terraformed_secret", "secret3", "secret4"],
                    env=env,
                ),
            ],
        ]
        return paginator

    def setup_copy(self, mock_application, source, target):

        self.application = mock_application
        self.load_application_mock = MagicMock()

        mocks = {}
        for env, stage in [(source, "source"), (target, "target")]:
            if env not in self.application.environments:
                continue  # skip envs that dont exist

            mock_session = MagicMock(name=f"{env}-session-mock")
            mock_sts_client = MagicMock(name=f"{env}-sts-client-mock")
            mock_sts_client.get_caller_identity.return_value = {
                "Arn": f"arn:sts:assume-role/{env}/something"
            }
            mock_iam_client = MagicMock(name=f"{env}-iam-client-mock")
            mock_ssm_client = MagicMock(name=f"{env}-ssm-client-mock")

            decision = "allowed"
            if not self.has_access.get(env, "skip"):
                decision = "implicitDeny"
            if stage == "source":
                mock_iam_client.simulate_principal_policy.side_effect = [
                    AWSTestFixtures.simulate_principal_policy_response(
                        action="ssm:GetParameter", decision=decision
                    )
                ]
            elif stage == "target":
                mock_iam_client.simulate_principal_policy.side_effect = [
                    AWSTestFixtures.simulate_principal_policy_response(decision=decision)
                ]

            if stage == "source":
                mock_ssm_client.get_paginator.return_value = (
                    self._create_parameters_by_path_paginator(source)
                )
                mock_ssm_client.list_tags_for_resource.side_effect = [
                    AWSTestFixtures.list_tags_for_resource_response(env=env, platform="copilot"),
                    AWSTestFixtures.list_tags_for_resource_response(env=env, platform="copilot"),
                    AWSTestFixtures.list_tags_for_resource_response(env=env),
                    AWSTestFixtures.list_tags_for_resource_response(
                        env=env, managed_by="DBT Platform - Terraform"
                    ),
                    AWSTestFixtures.list_tags_for_resource_response(env=env),
                    AWSTestFixtures.list_tags_for_resource_response(env=env),
                ]
            if stage == "target":

                def _create_ssm_mock_with_failing_put_parameter(ssm_client, calls_to_fail_on=[2]):
                    return_value = ssm_client.put_parameter.return_value

                    def mock_put_parameter(*args, **kwargs):
                        if not hasattr(mock_put_parameter, "call_count"):
                            mock_put_parameter.call_count = 0
                        if mock_put_parameter.call_count in calls_to_fail_on:
                            mock_put_parameter.call_count += 1
                            raise AWSTestFixtures.put_parameter_already_exists_error_response()
                        mock_put_parameter.call_count += 1
                        return return_value

                    ssm_client.put_parameter.side_effect = mock_put_parameter

                if self.put_parameter_unexpected:
                    mock_ssm_client.put_parameter.side_effect = (
                        AWSTestFixtures.client_error_response("PutParameter")
                    )
                else:
                    _create_ssm_mock_with_failing_put_parameter(mock_ssm_client)

            mocks[env] = {
                "session": mock_session,
            }

            mock_session.client.side_effect = self.__make_client_side_effect(
                mock_sts_client, mock_iam_client, mock_ssm_client
            )
            self.application.environments[env].sessions[
                self.application.environments[env].account_id
            ] = mock_session

        self.mocks = mocks

        self.load_application_mock.return_value = mock_application

        self.io_mock = MagicMock()

        return dict(
            load_application=self.load_application_mock,
            io=self.io_mock,
        )


@pytest.mark.parametrize(
    "input_args, params_exist",
    [
        ({"app_name": "test-application", "name": "secret", "overwrite": False}, "none"),
        ({"app_name": "test-application", "name": "secret", "overwrite": True}, "exists"),
        ({"app_name": "test-application", "name": "secret", "overwrite": False}, "none"),
    ],
)
def test_create(mock_application, input_args, params_exist):

    mock = AWSMocks(create_existing_params=params_exist)
    input_mocks = mock.setup_create(mock_application)
    secrets = Secrets(**input_mocks)

    secrets.create(**input_args)

    i = 1
    info_calls = []
    input_calls = []
    debug_calls = []
    for account_id, mocked in mock.mocks.items():
        env = mocked["env"]
        mocked["session"].client("sts").get_caller_identity.assert_called()
        mocked["session"].client("iam").simulate_principal_policy.assert_called_with(
            **AWSTestFixtures.simulate_principal_policy_called_with(account_id, env)
        )

    for env, data in mock.application.environments.items():

        data.session.client("ssm").put_parameter.assert_has_calls(
            [
                call(
                    **AWSTestFixtures.put_parameter_called_with(
                        env, i, overwrite=input_args["overwrite"]
                    )
                )
            ]
        )

        input_calls.append(
            call(
                f"Please enter value for secret 'SECRET' in environment '{env}'",
                hide_input=True,
            )
        )

        debug_calls.append(
            call(
                f"Creating AWS Parameter Store secret /platform/test-application/{env}/secrets/SECRET ..."
            )
        )

        debug_calls.append(
            call(
                f"Successfully created AWS Parameter Store secret /platform/test-application/{env}/secrets/SECRET"
            )
        )

        i += 1

    info_calls.append(
        call(
            "\nTo check or update your secrets, log into your AWS account via the Console and visit the Parameter Store https://eu-west-2.console.aws.amazon.com/systems-manager/parameters/\nYou can attach secrets into ECS container by adding them to the `secrets` section of your 'service-config.yml' file."
        )
    )
    info_calls.append(
        call(
            message="```\nsecrets:\n\tSECRET: /platform/${PLATFORM_APPLICATION_NAME}/${PLATFORM_ENVIRONMENT_NAME}/secrets/SECRET\n```",
            fg="cyan",
            bold=True,
        )
    )

    mock.io_mock.info.assert_has_calls(info_calls)
    mock.io_mock.input.assert_has_calls(input_calls)
    mock.io_mock.debug.assert_has_calls(debug_calls)


def test_create_no_access(mock_application):

    mock = AWSMocks(has_access={"all": False})
    input_mocks = mock.setup_create(mock_application)
    secrets = Secrets(**input_mocks)

    with pytest.raises(
        PlatformException,
        match="""You do not have AWS Parameter Store write access to the following AWS accounts: '000000000', '111111111', '222222222', '333333333'""",
    ):
        secrets.create("test-application", "secret", False)


def test_create_exception_parameter_found(mock_application):

    mock = AWSMocks(create_existing_params="exists")
    input_mocks = mock.setup_create(mock_application)
    secrets = Secrets(**input_mocks)

    with pytest.raises(
        PlatformException,
        match="""AWS Parameter Store secret 'SECRET' already exists for the following environments: 'development', 'staging', 'production', 'prod', 'test'.""",
    ):
        secrets.create("test-application", "secret", False)


def test_create_exception_unexpected(mock_application):

    mock = AWSMocks(create_existing_params="unexpected")
    input_mocks = mock.setup_create(mock_application)
    secrets = Secrets(**input_mocks)

    with pytest.raises(
        PlatformException,
        match=re.escape(
            """An error occurred (Unexpected) when calling the GetParameter operation: Simulated failure"""
        ),
    ):
        secrets.create("test-application", "secret", False)


@pytest.mark.parametrize(
    "input_args",
    [
        ({"app_name": "test-application", "source": "development", "target": "staging"}),
        ({"app_name": "test-application", "source": "development", "target": "prod"}),
    ],
)
def test_secrets_copy(mock_application, input_args):

    source = input_args["source"]
    target = input_args["target"]
    aws_mocks = AWSMocks()
    inputs = aws_mocks.setup_copy(mock_application, source, target)

    secrets = Secrets(**inputs)
    secrets.copy(**input_args)

    source_env = mock_application.environments[input_args["source"]]
    target_env = mock_application.environments[input_args["target"]]

    source_env.session.client("iam").simulate_principal_policy.assert_called_with(
        **AWSTestFixtures.simulate_principal_policy_called_with(
            source_env.account_id, source, ["ssm:GetParameter"]
        )
    )
    target_env.session.client("iam").simulate_principal_policy.assert_called_with(
        **AWSTestFixtures.simulate_principal_policy_called_with(
            target_env.account_id,
            target,
        )
    )

    source_env.session.client("ssm").get_paginator(
        "get_ssm_parameters_by_path"
    ).paginate.assert_has_calls(
        [
            call(
                **AWSTestFixtures.get_ssm_parameters_by_path_called_with(source, platform="copilot")
            ),
            call(**AWSTestFixtures.get_ssm_parameters_by_path_called_with(source)),
        ]
    )

    aws_mocks.io_mock.debug.assert_has_calls(
        [
            call(
                f"Creating AWS Parameter Store secret /copilot/test-application/{target}/secrets/SECRET1 ..."
            ),
            call(
                f"Creating AWS Parameter Store secret /copilot/test-application/{target}/secrets/SECRET2 ..."
            ),
            call(
                f"Creating AWS Parameter Store secret /platform/test-application/{target}/secrets/SECRET_EXISTS ..."
            ),
            call(
                f"Skipping AWS Parameter Store secret /platform/test-application/{target}/secrets/TERRAFORMED_SECRET with managed-by: DBT Platform - Terraform"
            ),
            call(
                f"Creating AWS Parameter Store secret /platform/test-application/{target}/secrets/SECRET3 ..."
            ),
            call(
                f"Creating AWS Parameter Store secret /platform/test-application/{target}/secrets/SECRET4 ..."
            ),
        ]
    )
    aws_mocks.io_mock.warn.assert_called_with(
        f"""The "SECRET_EXISTS" parameter already exists for the "{target}" environment."""
    )

    def sort_tags(mock_call):
        sorted_tags = sorted(mock_call["Tags"], key=lambda x: x["Key"])
        return call(
            Name=mock_call["Name"],
            Value=mock_call["Value"],
            Overwrite=mock_call["Overwrite"],
            Type=mock_call["Type"],
            Description=mock_call["Description"],
            Tags=sorted_tags,
        )

    actual_calls = target_env.session.client("ssm").put_parameter.call_args_list
    expected_calls = [
        call(
            **AWSTestFixtures.put_parameter_copied_called_with(
                "copilot",
                source,
                target,
                "secret1",
                tags=[
                    {"Key": "copilot-application", "Value": "test-application"},
                    {"Key": "copilot-environment", "Value": target},
                ],
            )
        ),
        call(
            **AWSTestFixtures.put_parameter_copied_called_with(
                "copilot",
                source,
                target,
                "secret2",
                tags=[
                    {"Key": "copilot-application", "Value": "test-application"},
                    {"Key": "copilot-environment", "Value": target},
                ],
            )
        ),
        call(
            **AWSTestFixtures.put_parameter_copied_called_with(
                "platform", source, target, "secret_exists"
            )
        ),
        call(
            **AWSTestFixtures.put_parameter_copied_called_with(
                "platform", source, target, "secret3"
            )
        ),
        call(
            **AWSTestFixtures.put_parameter_copied_called_with(
                "platform", source, target, "secret4"
            )
        ),
    ]

    sorted_actual = [sort_tags(c.args[0] if c.args else c.kwargs) for c in actual_calls]
    sorted_expected = [sort_tags(c.args[0] if c.args else c.kwargs) for c in expected_calls]

    assert sorted_actual == sorted_expected


@pytest.mark.parametrize(
    "input_args, expected_message, mocking",
    [
        (
            {
                "app_name": "test-application",
                "source": "development",
                "target": "target-doesnt-exist",
            },
            """Environment 'target-doesnt-exist' not found for application 'test-application'.""",
            {"has_access": {"development": True}},
        ),
        (
            {"app_name": "test-application", "source": "source-doesnt-exist", "target": "staging"},
            """Environment 'source-doesnt-exist' not found for application 'test-application'.""",
            {"has_access": {"staging": True}},
        ),
        (
            {"app_name": "test-application", "source": "development", "target": "staging"},
            """You do not have AWS Parameter Store read access to the following AWS accounts: '000000000'""",
            {
                "has_access": {
                    "development": False,
                    "staging": True,
                }
            },
        ),
        (
            {"app_name": "test-application", "source": "development", "target": "staging"},
            """You do not have AWS Parameter Store write access to the following AWS accounts: '111111111'""",
            {
                "has_access": {
                    "development": True,
                    "staging": False,
                }
            },
        ),
        (
            {"app_name": "test-application", "source": "production", "target": "staging"},
            """Cannot transfer secrets out from 'production' in the prod account '222222222' to 'staging' in '111111111'""",
            {
                "has_access": {
                    "production": True,
                    "staging": True,
                }
            },
        ),
        (
            {"app_name": "test-application", "source": "development", "target": "staging"},
            """An error occurred (Unexpected) when calling the PutParameter operation: Simulated failure""",
            {
                "has_access": {
                    "development": True,
                    "staging": True,
                },
                "put_parameter_unexpected": True,
            },
        ),
    ],
)
def test_secrets_copy_exception_raised(mock_application, input_args, expected_message, mocking):

    aws_mocks = AWSMocks(**mocking)
    inputs = aws_mocks.setup_copy(mock_application, input_args["source"], input_args["target"])

    secrets = Secrets(**inputs)

    with pytest.raises(
        PlatformException,
        match=re.escape(expected_message),
    ):
        secrets.copy(**input_args)
