from unittest.mock import Mock

from dbt_platform_helper.providers.aws.sso_auth import SSOAuthProvider

TEST_CLIENT_ID = "TEST_CLIENT_ID"

TEST_START_URL = "TEST_START_URL"

TEST_CLIENT_SECRET = "TEST_CLIENT_SECRET"

TEST_VERIFICATION_URI = "TEST_VERIFICATION_URI"

TEST_DEVICE_CODE = "TEST_DEVICE_CODE"


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
