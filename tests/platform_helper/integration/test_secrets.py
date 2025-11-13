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
    def list_tags_for_resource_response():
        pass

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
        pass

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


class CreateMock:
    def __init__(self, has_access=True, create_existing_params="none"):
        self.create_existing_params = create_existing_params
        self.has_access = has_access
        self.mocks = None

    def setup(self, mock_application):

        self.application = mock_application
        self.load_application_mock = MagicMock()
        self._create_sessions()
        self.load_application_mock.return_value = mock_application
        self._create_existing_params()

        self.io_mock = MagicMock()
        self.io_mock.input.side_effect = ["1", "2", "3", "4", "5"]

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
                {"Name": "doesntmatter4"},
            ]
        elif self.create_existing_params == "unexpected":
            self.parameter_store_mock.get_ssm_parameter_by_name.side_effect = [
                AWSTestFixtures.client_error_response("GetParameter")
            ]
        else:
            self.parameter_store_mock.get_ssm_parameter_by_name.side_effect = [
                AWSTestFixtures.get_parameter_not_found_error_response(),
                AWSTestFixtures.get_parameter_not_found_error_response(),
                AWSTestFixtures.get_parameter_not_found_error_response(),
                AWSTestFixtures.get_parameter_not_found_error_response(),
                AWSTestFixtures.get_parameter_not_found_error_response(),
            ]
        self.parameter_store_provider_mock.return_value = self.parameter_store_mock

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

            if self.has_access:
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


@pytest.mark.parametrize(
    "input_args, params_exist",
    [
        ({"app_name": "test-application", "name": "secret", "overwrite": False}, "none"),
        ({"app_name": "test-application", "name": "secret", "overwrite": True}, "exists"),
        ({"app_name": "test-application", "name": "secret", "overwrite": False}, "none"),
    ],
)
def test_create(mock_application, input_args, params_exist):

    mock = CreateMock(create_existing_params=params_exist)
    input_mocks = mock.setup(mock_application)
    secrets = Secrets(**input_mocks)

    secrets.create(**input_args)

    i = 1
    put_parameter_calls = []
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

        put_parameter_calls.append(
            call(
                AWSTestFixtures.put_parameter_called_with(env, i, overwrite=input_args["overwrite"])
            )
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
    mock.parameter_store_mock.put_parameter.assert_has_calls(put_parameter_calls)


def test_create_no_access(mock_application):

    mock = CreateMock(has_access=False)
    input_mocks = mock.setup(mock_application)
    secrets = Secrets(**input_mocks)

    with pytest.raises(
        PlatformException,
        match="""You do not have AWS Parameter Store write access to the following AWS accounts: '000000000', '111111111', '222222222', '333333333'""",
    ):
        secrets.create("test-application", "secret", False)


def test_create_exception_parameter_found(mock_application):

    mock = CreateMock(create_existing_params="exists")
    input_mocks = mock.setup(mock_application)
    secrets = Secrets(**input_mocks)

    with pytest.raises(
        PlatformException,
        match="""AWS Parameter Store secret 'SECRET' already exists for the following environments: 'development', 'staging', 'production', 'prod', 'test'.""",
    ):
        secrets.create("test-application", "secret", False)


def test_create_exception_unexpected(mock_application):

    mock = CreateMock(create_existing_params="unexpected")
    input_mocks = mock.setup(mock_application)
    secrets = Secrets(**input_mocks)

    with pytest.raises(
        PlatformException,
        match=re.escape(
            """An error occurred (Unexpected) when calling the GetParameter operation: Simulated failure"""
        ),
    ):
        secrets.create("test-application", "secret", False)


def make_client_side_effect(mock_sts_client, mock_iam_client, mock_ssm_client):
    def client_side_effect(service):
        return {
            "sts": mock_sts_client,
            "iam": mock_iam_client,
            "ssm": mock_ssm_client,
        }.get(service)

    return client_side_effect


@pytest.mark.parametrize(
    "input_args",
    [
        ({"app_name": "test-application", "source": "development", "target": "staging"}),
        # ({"source": "development", "target": "prod"}),
        # ({"source": "prod", "target": "development"}),
    ],
)
def test_secrets_copy(mock_application, input_args):

    load_application_mock = MagicMock()
    source = input_args["source"]
    target = input_args["target"]
    mocks = {}
    for env, stage in [(source, "source"), (target, "target")]:
        if env not in mock_application.environments:
            continue  # skip envs that dont exist
        mock_session = MagicMock(name=f"{env}-session-mock")
        mock_sts_client = MagicMock(name=f"{env}-sts-client-mock")
        mock_sts_client.get_caller_identity.return_value = {
            "Arn": f"arn:sts:assume-role/{env}/something"
        }
        mock_iam_client = MagicMock(name=f"{env}-iam-client-mock")
        mock_ssm_client = MagicMock(name=f"{env}-ssm-client-mock")

        decision = "allowed"
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

        def _create_parameters_by_path_paginator():
            paginator = Mock()
            paginator.paginate.side_effect = [
                [
                    AWSTestFixtures.get_parameter_by_path_response(
                        secrets=["secret1", "secret2"], env=source, platform="copilot"
                    ),
                ],
                [
                    AWSTestFixtures.get_parameter_by_path_response(
                        secrets=["secret_EXISTS", "terraformed_secret", "secret3", "secret4"],
                        env=source,
                    ),
                ],
            ]
            return paginator

        # def get_paginator(operation_name):
        #     _paginators = {}
        #     if operation_name == "get_parameters_by_path":
        #         _paginators[operation_name] = _create_parameters_by_path_paginator()
        #     else:
        #         _paginators[operation_name] = Mock()

        #     return _paginators[operation_name]

        if stage == "source":
            mock_ssm_client.get_paginator.return_value = _create_parameters_by_path_paginator()
            mock_ssm_client.list_tags_for_resource.side_effect = [
                {
                    "TagList": [
                        {"Key": "copilot-application", "Value": "test-application"},
                        {"Key": "copilot-environment", "Value": env},
                    ]
                },
                {
                    "TagList": [
                        {"Key": "copilot-application", "Value": "test-application"},
                        {"Key": "copilot-environment", "Value": env},
                    ]
                },
                {
                    "TagList": [
                        {"Key": "application", "Value": "test-application"},
                        {"Key": "environment", "Value": env},
                        {"Key": "managed-by", "Value": "DBT Platform"},
                    ]
                },
                {
                    "TagList": [
                        {"Key": "application", "Value": "test-application"},
                        {"Key": "environment", "Value": env},
                        {"Key": "managed-by", "Value": "DBT Platform - Terraform"},
                    ]
                },
                {
                    "TagList": [
                        {"Key": "application", "Value": "test-application"},
                        {"Key": "environment", "Value": env},
                        {"Key": "managed-by", "Value": "DBT Platform"},
                    ]
                },
                {
                    "TagList": [
                        {"Key": "application", "Value": "test-application"},
                        {"Key": "environment", "Value": env},
                        {"Key": "managed-by", "Value": "DBT Platform"},
                    ]
                },
            ]
        if stage == "target":

            def _create_ssm_mock_with_failing_put_parameter(ssm_client, calls_to_fail_on=[2]):
                original_put_parameter = ssm_client.put_parameter

                def mock_put_parameter(*args, **kwargs):

                    if not hasattr(mock_put_parameter, "assert_has_calls"):
                        mock_put_parameter.assert_has_calls = mock_assert_has_calls
                    if not hasattr(mock_put_parameter.assert_has_calls, "calls"):
                        mock_put_parameter.assert_has_calls.calls = []
                    if not hasattr(mock_put_parameter, "call_count"):
                        mock_put_parameter.call_count = 0

                    mock_put_parameter.assert_has_calls.calls.append(call(*args, **kwargs))
                    if mock_put_parameter.call_count in calls_to_fail_on:
                        mock_put_parameter.call_count += 1
                        raise ClientError(
                            {
                                "Error": {
                                    "Code": "ParameterAlreadyExists",
                                    "Message": "Simulated failure",
                                }
                            },
                            "CreateRule",
                        )
                    mock_put_parameter.call_count += 1
                    return original_put_parameter(*args, **kwargs)

                def mock_assert_has_calls(calls):
                    # print(calls[0].call_list())
                    # print(calls[0].call_args)
                    # print(calls[0].call_args.args)
                    # print(calls[0].call_args.kwargs)
                    assert mock_assert_has_calls.calls == calls

                ssm_client.put_parameter = mock_put_parameter

            _create_ssm_mock_with_failing_put_parameter(mock_ssm_client)

        mocks[env] = {
            "session": mock_session,
        }

        mock_session.client.side_effect = make_client_side_effect(
            mock_sts_client, mock_iam_client, mock_ssm_client
        )
        mock_application.environments[env].sessions[
            mock_application.environments[env].account_id
        ] = mock_session

    load_application_mock.return_value = mock_application

    io_mock = MagicMock()

    secrets = Secrets(
        io=io_mock,
        load_application=load_application_mock,
    )
    secrets.copy(**input_args)

    source_env = mock_application.environments[input_args["source"]]
    target_env = mock_application.environments[input_args["target"]]

    source_env.session.client("iam").simulate_principal_policy.assert_called_with(
        PolicySourceArn=f"arn:aws:iam::{source_env.account_id}:role/aws-reserved/sso.amazonaws.com/eu-west-2/{source}",
        ActionNames=["ssm:GetParameter"],
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
    target_env.session.client("iam").simulate_principal_policy.assert_called_with(
        PolicySourceArn=f"arn:aws:iam::{target_env.account_id}:role/aws-reserved/sso.amazonaws.com/eu-west-2/{target}",
        ActionNames=["ssm:PutParameter"],
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

    io_mock.debug.assert_has_calls(
        [
            call(
                f"Creating AWS Parameter Store secret /copilot/test-application/{target}/secrets/SECRET1 ..."
            ),
            call(
                f"Creating AWS Parameter Store secret /copilot/test-application/{target}/secrets/SECRET2 ..."
            ),
            call(
                "Creating AWS Parameter Store secret /platform/test-application/staging/secrets/SECRET_EXISTS ..."
            ),
            call(
                "Skipping AWS Parameter Store secret /platform/test-application/staging/secrets/TERRAFORMED_SECRET with managed-by: DBT Platform - Terraform"
            ),
            call(
                f"Creating AWS Parameter Store secret /platform/test-application/{target}/secrets/SECRET3 ..."
            ),
            call(
                f"Creating AWS Parameter Store secret /platform/test-application/{target}/secrets/SECRET4 ..."
            ),
        ]
    )
    io_mock.warn.assert_called_with(
        f"""The "SECRET_EXISTS" parameter already exists for the "{target}" environment."""
    )

    put_parameter_fixture = lambda mode, index, tags=[]: dict(
        Name=f"/{mode}/test-application/{target}/secrets/SECRET{index}",
        Value=f"secret{index}",
        Overwrite=False,
        Type="SecureString",
        Description=f"Copied from {source} environment.",
        Tags=tags
        + [
            {"Key": "application", "Value": "test-application"},
            {"Key": "environment", "Value": target},
            {"Key": "managed-by", "Value": MANAGED_BY_PLATFORM},
            {"Key": "copied-from", "Value": source},
        ],
    )

    # **AWSTestFixtures.put_parameter_copied_called_with(
    #     "copilot",source, target, "secret1",
    #     tags=[
    #         {"Key": "copilot-application", "Value": "test-application"},
    #         {"Key": "copilot-environment", "Value": target},
    #     ],
    # )
    target_env.session.client("ssm").put_parameter.assert_has_calls(
        [
            call(
                **put_parameter_fixture(
                    "copilot",
                    1,
                    [
                        {"Key": "copilot-application", "Value": "test-application"},
                        {"Key": "copilot-environment", "Value": target},
                    ],
                )
            ),
            call(
                **put_parameter_fixture(
                    "copilot",
                    2,
                    [
                        {"Key": "copilot-application", "Value": "test-application"},
                        {"Key": "copilot-environment", "Value": target},
                    ],
                )
            ),
            call(**put_parameter_fixture("platform", "_EXISTS")),
            call(**put_parameter_fixture("platform", 3)),
            call(**put_parameter_fixture("platform", 4)),
        ]
    )


# TODO add test where some variables already exist and assert they were called


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
            {"has_access": {"development": {"access": True, "stage": "source"}}},
        ),
        (
            {"app_name": "test-application", "source": "source-doesnt-exist", "target": "staging"},
            """Environment 'source-doesnt-exist' not found for application 'test-application'.""",
            {"has_access": {"staging": {"access": True, "stage": "target"}}},
        ),
        (
            {"app_name": "test-application", "source": "development", "target": "staging"},
            """You do not have AWS Parameter Store read access to the following AWS accounts: '000000000'""",
            {
                "has_access": {
                    "development": {"access": False, "stage": "source"},
                    "staging": {"access": True, "stage": "target"},
                }
            },
        ),
        (
            {"app_name": "test-application", "source": "development", "target": "staging"},
            """You do not have AWS Parameter Store write access to the following AWS accounts: '111111111'""",
            {
                "has_access": {
                    "development": {"access": True, "stage": "source"},
                    "staging": {"access": False, "stage": "target"},
                }
            },
        ),
        (
            {"app_name": "test-application", "source": "production", "target": "staging"},
            """Cannot transfer secrets out from 'production' in the prod account '222222222' to 'staging' in '111111111'""",
            {
                "has_access": {
                    "production": {"access": True, "stage": "source"},
                    "staging": {"access": True, "stage": "target"},
                }
            },
        ),
    ],
)
def test_secrets_copy_exception_raised(mock_application, input_args, expected_message, mocking):

    load_application_mock = MagicMock()

    mocks = {}

    for env in [input_args["source"], input_args["target"]]:
        if env not in mock_application.environments:
            continue  # skip envs that dont exist
        mock_session = MagicMock(name=f"{env}-session-mock")
        mock_sts_client = MagicMock(name=f"{env}-sts-client-mock")
        mock_sts_client.get_caller_identity.return_value = {
            "Arn": f"arn:sts:assume-role/{env}/something"
        }
        mock_iam_client = MagicMock(name=f"{env}-iam-client-mock")
        mock_ssm_client = MagicMock(name=f"{env}-ssm-client-mock")

        calls = []
        if mocking.get("has_access", {}).get(env, {}):
            data = mocking["has_access"][env]
            action = "ssm:PutParameter"
            if data["stage"] == "source":
                action = "ssm:GetParameter"

            decision = "allowed"
            if not data["access"]:
                decision = "implicitDeny"

            calls.append(
                {
                    "EvaluationResults": [
                        {
                            "EvalActionName": action,
                            "EvalResourceName": "*",
                            "EvalDecision": decision,
                            "MatchedStatements": [],
                        }
                    ],
                }
            )

        mock_iam_client.simulate_principal_policy.side_effect = calls
        mocks[env] = {
            "session": mock_session,
        }

        mock_session.client.side_effect = make_client_side_effect(
            mock_sts_client, mock_iam_client, mock_ssm_client
        )
        mock_application.environments[env].sessions[
            mock_application.environments[env].account_id
        ] = mock_session

    load_application_mock.return_value = mock_application

    io_mock = MagicMock()

    parameter_store_mock = MagicMock()
    parameter_store_mock.return_value = MagicMock()

    secrets = Secrets(
        io=io_mock,
        load_application=load_application_mock,
        parameter_store_provider=parameter_store_mock,
    )

    with pytest.raises(
        PlatformException,
        match=re.escape(expected_message),
    ):
        secrets.copy(**input_args)
