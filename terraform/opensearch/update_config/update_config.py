import base64
import json
from urllib.parse import unquote
from urllib.parse import urlparse

import boto3
import urllib3

http = urllib3.PoolManager()


def get_admin_user_and_host(ssm, ssm_param_name):
    raw = ssm.get_parameter(Name=ssm_param_name, WithDecryption=True)["Parameter"]["Value"]

    parsed = urlparse(raw)

    admin_user = {"username": parsed.username, "password": unquote(parsed.password)}
    host = f"{parsed.scheme}://{parsed.hostname}"

    return admin_user, host


def enable_audit_logging(host, admin_user):
    """
    ref - https://registry.terraform.io/providers/opensearch-project/opensearch/latest/docs/resources/audit_config
    ref - https://docs.opensearch.org/latest/security/audit-logs/index/
    ref - https://docs.aws.amazon.com/opensearch-service/latest/developerguide/audit-logs.html

    """

    body = {
        "enabled": True,
        "audit": {
            "ignore_users": [],
            "ignore_requests": [],
            "ignore_headers": [],
            "ignore_url_params": [],
            "disabled_rest_categories": [],
            "disabled_transport_categories": [],
            "resolve_bulk_requests": False,
            "exclude_sensitive_headers": True,
            "enable_transport": False,
            "log_request_body": False,
            "resolve_indices": True,
            "enable_rest": True,
        },
        "compliance": {
            "enabled": True,
            "write_log_diffs": True,
            "read_watched_fields": {},
            "read_ignore_users": [],
            "write_watched_indices": [],
            "write_ignore_users": [],
            "read_metadata_only": True,
            "write_metadata_only": True,
            "external_config": False,
            "internal_config": True,
        },
    }
    path = "/audit/config"
    response = request("PUT", host, path, admin_user, body)
    return response


def request(method, host, path, admin_user, body=None):
    url = f"{host.rstrip('/')}/_plugins/_security/api{path}"
    raw = admin_user["username"] + ":" + admin_user["password"]
    base = base64.b64encode(raw.encode("utf-8")).decode("utf-8")

    headers = {"Authorization": f"Basic {base}", "Content-Type": "application/json"}

    response = http.request(
        method,
        url,
        body=json.dumps(body).encode("utf-8") if body else None,
        headers=headers,
    )
    if response.status not in (200, 201):
        raise RuntimeError(
            f"API error[{response.status}] {method} {path}: {response.data.decode()}"
        )

    return json.loads(response.data.decode("utf-8"))


def handler(event, context):
    """
    Expected Event:
    {
        "AdminUserEndpointParam": "/opensearch-endpoint",
        "Application" : "my-app",
        "Environment" : "production",
    }
    """
    print("REQUEST RECEIVED:\n" + json.dumps(event))

    ssm = boto3.client("ssm")

    admin_user, host = get_admin_user_and_host(ssm, event["AdminUserEndpointParam"])

    application = event["Application"]
    environment = event["Environment"]

    response = enable_audit_logging(host=host, admin_user=admin_user)

    message = (
        "REQUEST COMPLETE:\n" f"For environment {environment} in app {application}\n" f"{response}"
    )
    print(message)
