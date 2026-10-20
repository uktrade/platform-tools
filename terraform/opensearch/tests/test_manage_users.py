from unittest.mock import patch

import pytest

from terraform.opensearch.manage_users import configure_audit_logging
from terraform.opensearch.manage_users import get_audit_configuration


AUDIT_CONFIGURATION = {
    "enabled": True,
    "audit": {
        "enable_rest": True,
        "enable_transport": True,
        "disabled_rest_categories": ["AUTHENTICATED", "GRANTED_PRIVILEGES"],
        "disabled_transport_categories": ["AUTHENTICATED", "GRANTED_PRIVILEGES"],
        "resolve_bulk_requests": False,
        "log_request_body": False,
        "resolve_indices": True,
    },
}


def test_get_audit_configuration_uses_v1_request_body():
    assert get_audit_configuration(1) == {"config": AUDIT_CONFIGURATION}


def test_get_audit_configuration_uses_v2_request_body():
    assert get_audit_configuration(2) == AUDIT_CONFIGURATION


def test_get_audit_configuration_rejects_unsupported_version():
    with pytest.raises(ValueError, match="Unsupported OpenSearch major version: 3"):
        get_audit_configuration(3)


@patch("terraform.opensearch.manage_users.request")
def test_configure_audit_logging_sends_version_specific_body(mock_request):
    admin_user = {"username": "admin", "password": "password"}
    mock_request.return_value = {"status": "OK"}

    result = configure_audit_logging("https://search.example", admin_user, 1)

    mock_request.assert_called_once_with(
        "PUT",
        "https://search.example",
        "/audit/config",
        admin_user,
        {"config": AUDIT_CONFIGURATION},
    )
    assert result == {"status": "OK"}
