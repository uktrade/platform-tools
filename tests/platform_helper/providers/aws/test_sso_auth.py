from unittest.mock import Mock

import botocore
import pytest

from dbt_platform_helper.providers.aws.sso_auth import SSOAuthProvider

TEST_CLIENT_ID = "TEST_CLIENT_ID"

TEST_START_URL = "TEST_START_URL"

TEST_CLIENT_SECRET = "TEST_CLIENT_SECRET"

TEST_VERIFICATION_URI = "TEST_VERIFICATION_URI"

TEST_DEVICE_CODE = "TEST_DEVICE_CODE"

TEST_ACCESS_TOKEN = "TEST_ACCESS_TOKEN"


def test_register_returns_client_id_and_client_secret():
    mock_boto_sso_client = Mock(name="client-mock")
    mock_boto_sso_client.register_client.return_value = {
        "clientId": TEST_CLIENT_ID,
        "clientSecret": TEST_CLIENT_SECRET,
    }
    mock_session = Mock(name="session-mock")
    mock_session.client.return_value = mock_boto_sso_client

    client_id, client_secret = SSOAuthProvider(mock_session).register(
        client_name="platform-helper", client_type="public"
    )

    mock_boto_sso_client.register_client.assert_called_once_with(
        clientName="platform-helper", clientType="public"
    )
    assert client_id == TEST_CLIENT_ID
    assert client_secret == TEST_CLIENT_SECRET


def test_start_device_authorization_returns_device_code_and_url():
    mock_boto_sso_client = Mock(name="client-mock")
    mock_boto_sso_client.start_device_authorization.return_value = {
        "verificationUriComplete": TEST_VERIFICATION_URI,
        "deviceCode": TEST_DEVICE_CODE,
    }
    mock_session = Mock(name="session-mock")
    mock_session.client.return_value = mock_boto_sso_client

    url, device_code = SSOAuthProvider(mock_session).start_device_authorization(
        client_id=TEST_CLIENT_ID, client_secret=TEST_CLIENT_SECRET, start_url=TEST_START_URL
    )

    mock_boto_sso_client.start_device_authorization.assert_called_once_with(
        client_id=TEST_CLIENT_ID, client_secret=TEST_CLIENT_SECRET, start_url=TEST_START_URL
    )
    assert url == TEST_VERIFICATION_URI
    assert device_code == TEST_DEVICE_CODE


def test_list_accounts():
    mock_boto_sso_client = Mock(name="client-mock")
    mock_boto_sso_client.list_accounts.return_value = {
        "accountList": {"accountName": "test-account", "accountId": "abc123"}
    }
    mock_session = Mock(name="session-mock")
    mock_session.client.return_value = mock_boto_sso_client

    result = SSOAuthProvider(mock_session).list_accounts(TEST_ACCESS_TOKEN)

    assert result == {"accountName": "test-account", "accountId": "abc123"}


class TestCreateAccessToken:
    def test_creates_access_token(self):
        mock_boto_sso_client = Mock(name="client-mock")
        mock_boto_sso_client.create_access_token.return_value = TEST_ACCESS_TOKEN
        mock_session = Mock(name="session-mock")
        mock_session.client.return_value = mock_boto_sso_client

        result = SSOAuthProvider(mock_session).create_access_token(
            TEST_CLIENT_ID, TEST_CLIENT_SECRET, TEST_DEVICE_CODE
        )

        assert result == TEST_ACCESS_TOKEN

    def test_raises_error_when_error_code_is_not_authorization_pending_exception(self):
        mock_boto_sso_client = Mock(name="client-mock")
        mock_boto_sso_client.create_access_token.side_effect = botocore.exceptions.ClientError(
            {
                "Error": {"Code": "TestException"},
            },
            operation_name="CreateAccessToken",
        )
        mock_session = Mock(name="session-mock")
        mock_session.client.return_value = mock_boto_sso_client

        with pytest.raises(botocore.exceptions.ClientError):
            SSOAuthProvider(mock_session).create_access_token(
                TEST_CLIENT_ID, TEST_CLIENT_SECRET, TEST_DEVICE_CODE
            )

    def test_does_not_raise_when_error_code_is_authorization_pending_exception(self):
        mock_boto_sso_client = Mock(name="client-mock")
        mock_boto_sso_client.create_access_token.side_effect = botocore.exceptions.ClientError(
            {
                "Error": {"Code": "AuthorizationPendingException"},
            },
            operation_name="CreateAccessToken",
        )
        mock_session = Mock(name="session-mock")
        mock_session.client.return_value = mock_boto_sso_client

        try:
            SSOAuthProvider(mock_session).create_access_token(
                TEST_CLIENT_ID, TEST_CLIENT_SECRET, TEST_DEVICE_CODE
            )
        except botocore.exceptions.ClientError as e:
            pytest.fail(f"Unexpected exception: {e}")
