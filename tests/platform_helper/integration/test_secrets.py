from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from dbt_platform_helper.constants import MANAGED_BY_PLATFORM
from dbt_platform_helper.domain.secrets import Secrets
from dbt_platform_helper.platform_exception import PlatformException


class MockAWSSession:
    pass


# TODO when param not found throw client error and not return empty list
# TODO create exception for unexpected client error
@pytest.mark.parametrize(
    "input_args, policies, params_exist",
    [
        ({"app_name": "test-application", "name": "secret", "overwrite": False}, "admin", False),
        ({"app_name": "test-application", "name": "secret", "overwrite": True}, "inline", True),
        ({"app_name": "test-application", "name": "secret", "overwrite": False}, "inline", False),
    ],
)
def test_create(mock_application, input_args, policies, params_exist):

    mocks = {}
    for env, env_object in mock_application.environments.items():
        mock_session = MagicMock(name=f"{env}-session-mock")
        mock_sts_client = MagicMock(name=f"{env}-sts-client-mock")
        mock_sts_client.get_caller_identity.return_value = {
            "Arn": f"arn:sts:assume-role/{env}/something"
        }

        mock_iam_client = MagicMock(name=f"{env}-iam-client-mock")
        mock_ssm_client = MagicMock(name=f"{env}-ssm-client-mock")

        if policies == "admin":
            mock_iam_client.list_attached_role_policies.return_value = {
                "AttachedPolicies": [{"PolicyName": "AdministratorAccess"}]
            }
        else:
            mock_iam_client.list_attached_role_policies.return_value = {"AttachedPolicies": []}

        if policies == "inline":
            mock_iam_client.list_role_policies.return_value = {"PolicyNames": ["inline"]}
            mock_iam_client.get_role_policy.return_value = {
                "PolicyDocument": {"Statement": [{"Action": ["acm:*", "ssm:*"]}]}
            }
        else:
            mock_iam_client.list_role_policies.return_value = {"PolicyNames": []}

        mocks[env] = {
            "session": mock_session,
        }

        def make_client_side_effect(mock_sts_client, mock_iam_client, mock_ssm_client):
            def client_side_effect(service):
                return {
                    "sts": mock_sts_client,
                    "iam": mock_iam_client,
                    "ssm": mock_ssm_client,
                }.get(service)

            return client_side_effect

        mock_session.client.side_effect = make_client_side_effect(
            mock_sts_client, mock_iam_client, mock_ssm_client
        )
        mock_application.environments[env].sessions[
            mock_application.environments[env].account_id
        ] = mock_session

    load_application_mock = MagicMock()
    load_application_mock.return_value = mock_application
    io_mock = MagicMock()
    io_mock.input.side_effect = ["1", "2", "3", "4"]
    parameter_store_provider_mock = MagicMock()

    parameter_store_mock = MagicMock()
    if params_exist:
        parameter_store_mock.get_ssm_parameter_by_name.side_effect = [
            {"Name": "doesntmatter"},
            {"Name": "doesntmatter1"},
            {"Name": "doesntmatter2"},
            {"Name": "doesntmatter3"},
        ]
    else:
        parameter_store_mock.get_ssm_parameter_by_name.side_effect = [
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

    parameter_store_provider_mock.return_value = parameter_store_mock
    secrets = Secrets(
        load_application=load_application_mock,
        io=io_mock,
        parameter_store_provider=parameter_store_provider_mock,
    )

    secrets.create(**input_args)

    i = 1
    for env, mocked in mocks.items():
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
        mocked["session"].client("ssm").put_parameter.assert_called_with(**called_with)
        i += 1


def test_create_no_access(mock_application):

    mocks = {}
    for env, env_object in mock_application.environments.items():
        mock_session = MagicMock(name=f"{env}-session-mock")
        mock_sts_client = MagicMock(name=f"{env}-sts-client-mock")
        mock_sts_client.get_caller_identity.return_value = {
            "Arn": f"arn:sts:assume-role/{env}/something"
        }

        mock_iam_client = MagicMock(name=f"{env}-iam-client-mock")
        mock_iam_client.list_attached_role_policies.return_value = {"AttachedPolicies": []}
        mock_iam_client.list_role_policies.return_value = {"PolicyNames": []}

        mocks[env] = {
            "session": mock_session,
        }

        def make_client_side_effect(mock_sts_client, mock_iam_client):
            def client_side_effect(service):
                return {"sts": mock_sts_client, "iam": mock_iam_client}.get(service)

            return client_side_effect

        mock_session.client.side_effect = make_client_side_effect(mock_sts_client, mock_iam_client)
        mock_application.environments[env].sessions[
            mock_application.environments[env].account_id
        ] = mock_session

    load_application_mock = MagicMock()
    load_application_mock.return_value = mock_application
    io_mock = MagicMock()

    parameter_store_provider_mock = MagicMock()

    parameter_store_mock = MagicMock()

    parameter_store_mock.get_ssm_parameter_by_name.side_effect = [
        {"Name": "doesntmatter"},
        {"Name": "doesntmatter1"},
        {"Name": "doesntmatter2"},
        {"Name": "doesntmatter3"},
    ]
    parameter_store_provider_mock.return_value = parameter_store_mock

    secrets = Secrets(
        load_application=load_application_mock,
        io=io_mock,
    )

    with pytest.raises(
        PlatformException,
        match="""You do not have SSM write access to the following AWS accounts: 000000000, 111111111, 222222222, 333333333""",
    ):
        secrets.create("test-application", "secret", False)


def test_create_exception_parameter_found(mock_application):

    mocks = {}
    for env, env_object in mock_application.environments.items():
        mock_session = MagicMock(name=f"{env}-session-mock")
        mock_sts_client = MagicMock(name=f"{env}-sts-client-mock")
        mock_sts_client.get_caller_identity.return_value = {
            "Arn": f"arn:sts:assume-role/{env}/something"
        }

        mock_iam_client = MagicMock(name=f"{env}-iam-client-mock")
        mock_iam_client.list_attached_role_policies.return_value = {
            "AttachedPolicies": [{"PolicyName": "AdministratorAccess"}]
        }

        mocks[env] = {
            "session": mock_session,
        }

        def make_client_side_effect(mock_sts_client, mock_iam_client):
            def client_side_effect(service):
                return {"sts": mock_sts_client, "iam": mock_iam_client}.get(service)

            return client_side_effect

        mock_session.client.side_effect = make_client_side_effect(mock_sts_client, mock_iam_client)
        mock_application.environments[env].sessions[
            mock_application.environments[env].account_id
        ] = mock_session

    load_application_mock = MagicMock()
    load_application_mock.return_value = mock_application
    io_mock = MagicMock()

    parameter_store_provider_mock = MagicMock()

    parameter_store_mock = MagicMock()

    parameter_store_mock.get_ssm_parameter_by_name.side_effect = [
        {"Name": "doesntmatter"},
        {"Name": "doesntmatter1"},
        {"Name": "doesntmatter2"},
        {"Name": "doesntmatter3"},
    ]
    parameter_store_provider_mock.return_value = parameter_store_mock

    secrets = Secrets(
        load_application=load_application_mock,
        io=io_mock,
        parameter_store_provider=parameter_store_provider_mock,
    )

    with pytest.raises(
        PlatformException,
        match="""SSM parameter SECRET already exists for the following environments: development, staging, production, test.""",
    ):
        secrets.create("test-application", "secret", False)


# @pytest.mark.parametrize(
#     "input_args, env_vars, expected_results",
#     [
#         (
#             {"environment": "development", "services": []},
#         ),
#         (
#             {"environment": "development", "services": []},
#         ),
#         (
#             {"environment": "development", "services": []},
#         ),
#     ],
# )
# @patch(
#     "dbt_platform_helper.domain.service.version", return_value="14.0.0"
# )  # Fakefs breaks the metadata to retrieve package version
# @patch("dbt_platform_helper.providers.terraform_manifest.version", return_value="14.0.0")
# @freeze_time("2025-01-16 13:00:00")
# def test_generate(
#     mock_version,
#     fakefs,
#     create_valid_platform_config_file,
#     create_valid_service_config_file,
#     mock_application,
#     input_args,
#     env_vars,
#     expected_results,
# ):

#     # Test setup
#     if env_vars:
#         for var, value in env_vars.items():
#             os.environ[var] = value
#     load_application = Mock()
#     load_application.return_value = mock_application
#     mock_installed_version_provider = create_autospec(spec=InstalledVersionProvider, spec_set=True)
#     mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(14, 0, 0)
#     mock_config_validator = Mock(spec=ConfigValidator)
#     mock_config_provider = ConfigProvider(
#         mock_config_validator, installed_version_provider=mock_installed_version_provider
#     )

#     io = MagicMock()
#     service_manager = ServiceManager(
#         config_provider=mock_config_provider,
#         io=io,
#         load_application=load_application,
#     )

#     # Test execution
#     service_manager.generate(**input_args)

#     # Test Assertion
#     for environment, file in expected_results.items():
#         actual_terraform = Path(
#             f"terraform/services/{environment}/web/main.tf.json"
#         )  # Path where terraform manifest is generated
#         expected_terraform = (
#             EXPECTED_DATA_DIR / "services" / "terraform" / f"{file}"
#         )  # Location of expected results

#         assert actual_terraform.exists()

#         actual_content = actual_terraform.read_text()
#         expected_content = expected_terraform.read_text()
#         actual_json_content = json.loads(actual_content)
#         expected_json_content = json.loads(expected_content)

#         assert actual_json_content == expected_json_content

#     if env_vars:
#         for var, value in env_vars.items():
#             del os.environ[var]
