from unittest.mock import Mock

from dbt_platform_helper.providers.aws.sso_auth import SSOAuthProvider


def test_register_returns_client_id_and_client_secret():
    mock_boto_sso_client = Mock(name="client-mock")
    mock_boto_sso_client.register_client.return_value = {
        "clientId": "TEST_CLIENT_ID",
        "clientSecret": "TEST_CLIENT_SECRET",
    }
    mock_session = Mock(name="session-mock")
    mock_session.client.return_value = mock_boto_sso_client

    client_id, client_secret = SSOAuthProvider(mock_session).register(
        client_name="platform-helper", client_type="public"
    )

    mock_boto_sso_client.register_client.assert_called_once_with(
        clientName="platform-helper", clientType="public"
    )
    assert client_id == "TEST_CLIENT_ID"
    assert client_secret == "TEST_CLIENT_SECRET"
