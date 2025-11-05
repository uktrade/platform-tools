from unittest.mock import MagicMock

from dbt_platform_helper.domain.secrets import Secrets


def test_create(mock_application):

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
            "sts": mock_sts_client,
            "iam": mock_iam_client,
        }

        mock_session.client.side_effect = lambda service: {
            "sts": mocks[env]["sts"],
            "iam": mocks[env]["iam"],
        }.get(service)

        mock_application.environments[env].sessions[
            mock_application.environments[env].account_id
        ] = mock_session

    load_application_mock = MagicMock()
    load_application_mock.return_value = mock_application
    io_mock = MagicMock()

    secrets = Secrets(
        load_application=load_application_mock,
        io=io_mock,
    )

    secrets.create("test-application", "secret", False)

    print(mocks)
    for env, mocked in mocks.items():
        # print( mocked["session"])
        # print( mocked["session"].client("sts"))
        # print( mocked["session"].client("iam"))
        mocked["session"].client("sts").get_caller_identity.assert_called_once()
        mocked["session"].client("iam").list_attached_role_policies.assert_called_with(RoleName=env)

    assert False


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
