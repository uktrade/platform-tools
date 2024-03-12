from http import HTTPStatus
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from oauth2_client.credentials_manager import OAuthError

from dbt_platform_helper.utils.cloudfoundry import get_cloud_foundry_client_or_abort


@patch("dbt_platform_helper.utils.cloudfoundry.CloudFoundryClient")
def test_get_cloud_foundry_client_or_abort_success(mock_cf, capsys):
    mock_client = Mock()
    mock_cf.build_from_cf_config.return_value = mock_client

    client = get_cloud_foundry_client_or_abort()

    stdout = capsys.readouterr().out
    assert "Logged in to Cloud Foundry" in stdout
    assert client == mock_client


@patch("dbt_platform_helper.utils.cloudfoundry.CloudFoundryClient")
def test_get_cloud_foundry_client_or_abort_prints_useful_message_and_exits(mock_cf, capsys):
    exception = OAuthError(
        HTTPStatus(401),
        "invalid_token",
        "Invalid refresh token expired at Wed Aug 30 06:00:43 UTC 2023",
    )
    mock_cf.build_from_cf_config.side_effect = exception

    with pytest.raises(SystemExit) as ex:
        get_cloud_foundry_client_or_abort()

    stdout = capsys.readouterr().out
    assert ex.value.code == 1
    assert f"Could not connect to Cloud Foundry: {str(exception)}" in stdout
    assert "Please log in with: cf login" in stdout
