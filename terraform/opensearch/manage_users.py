import base64
import json
from urllib.parse import unquote
from urllib.parse import urlparse

import boto3
import urllib3
from botocore.exceptions import ClientError

http = urllib3.PoolManager()

READ_ROLE = "read_role"
WRITE_ROLE = "write_role"
INDEX_ROLE = "index_role"


def get_admin_user_and_host(ssm, ssm_param_name):
    raw = ssm.get_parameter(Name=ssm_param_name, WithDecryption=True)["Parameter"]["Value"]

    parsed = urlparse(raw)

    admin_user = {"username": parsed.username, "password": unquote(parsed.password)}
    host = f"{parsed.scheme}://{parsed.hostname}"

    return admin_user, host


def get_or_create_roles(host, admin_user):
    roles = {
        READ_ROLE: {
            "cluster_permissions": ["cluster_composite_ops_ro"],
            "index_permissions": [
                {
                    "index_patterns": ["*"],
                    "allowed_actions": [
                        "read",
                        "indices:data/read/*",
                        "indices:admin/mappings/fields/get*",
                        "indices:admin/get",
                    ],
                }
            ],
        },
        WRITE_ROLE: {
            "cluster_permissions": ["cluster_composite_ops"],
            "index_permissions": [
                {
                    "index_patterns": ["*"],
                    "allowed_actions": [
                        "write",
                        "read",  # Required: For bulk checks/updates
                        "manage",
                        "indices:data/write/*",
                    ],
                }
            ],
        },
        INDEX_ROLE: {
            "cluster_permissions": ["cluster_composite_ops"],
            "index_permissions": [
                {
                    "index_patterns": ["*"],
                    "allowed_actions": [
                        "create_index",
                        "manage",
                        "indices:admin/exists",
                        "indices:admin/get",  # Allows check if index exists
                        "indices:admin/create",
                    ],
                }
            ],
        },
    }
    existing_roles = {}
    for role_name, role in roles.items():
        try:
            existing_roles[role_name] = request("GET", host, f"/roles/{role_name}", admin_user)
        except Exception:
            existing_roles[role_name] = request(
                "PUT", host, f"/roles/{role_name}", admin_user, role
            )

    return existing_roles


def create_or_update_user(host, admin_user, new_user, roles):
    body = {
        "password": new_user["password"],
        "backend_roles": roles,
        "attributes": {},
    }
    username = new_user["username"]
    path = "/internalusers/" + username
    user_response = request("PUT", host, path, admin_user, body)

    for role in roles:
        try:
            map_response = request(
                "PUT", host, f"rolesmapping/{role}", admin_user, {"users": [username]}
            )
        except Exception:
            print(f"Failed to create user mapping for {username} to role {role}")
    return user_response


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


def create_or_update_user_secret(ssm, user_secret_name, user_secret_string, event):
    user_secret_description = event["SecretDescription"]
    application = event["Application"]
    environment = event["Environment"]

    user_secret = None

    try:
        user_secret = ssm.put_parameter(
            Name=user_secret_name,
            Description=user_secret_description,
            Value=json.dumps(user_secret_string),
            Tags=[
                {"Key": "managed-by", "Value": "DBT Platform - opensearch-create-users lambda"},
                {"Key": "application", "Value": application},
                {"Key": "environment", "Value": environment},
                {"Key": "copilot-application", "Value": application},
                {"Key": "copilot-environment", "Value": environment},
            ],
            Type="SecureString",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ParameterAlreadyExists":
            user_secret = ssm.put_parameter(
                Name=user_secret_name,
                Description=user_secret_description,
                Value=json.dumps(user_secret_string),
                Overwrite=True,
            )

    return user_secret


def handler(event, context):
    """
    Expected Event:
    {
        "AdminUserEndpointParam": "/opensearch-endpoint",
        "Application" : "my-app",
        "Environment" : "production",
        "SecretDescription": "description"
        "Users" : [
            "Username" : "reporting",
            "Index" : false,
            "Read" : true,
            "Write" : false
        ]
    }
    """
    print("REQUEST RECEIVED:\n" + json.dumps(event))

    secrets_manager = boto3.client("secretsmanager")
    ssm = boto3.client("ssm")

    admin_user, host = get_admin_user_and_host(ssm, event["AdminUserEndpointParam"])

    print(get_or_create_roles(host, admin_user))
    application = event["Application"]
    environment = event["Environment"]

    for user_config in event["Users"]:
        username = user_config["Username"]
        param_prefix = username.replace("-", "_").upper()
        ssm_param_name = (
            f"/platform/{application}/{environment}/secrets/{param_prefix}_OPENSEARCH_ENDPOINT"
        )

        role_map = {"Read": READ_ROLE, "Write": WRITE_ROLE, "Index": INDEX_ROLE}

        roles = [role_map[key] for key in role_map.keys() if user_config[key]]

        print("generating password ...")
        user_password = secrets_manager.get_random_password(
            PasswordLength=16,
            ExcludeCharacters='[]{}()"@/\\;=?&`><:|#',
            ExcludePunctuation=False,
            IncludeSpace=False,
        )["RandomPassword"]

        print(f"Creating user {username}...")
        create_or_update_user(
            host, admin_user, {"username": username, "password": user_password}, roles
        )

        parsed = urlparse(host)
        user_secret_string = f"https://{username}:{user_password}@{parsed.hostname}"

        print(f"Updating user {username} in ssm {ssm_param_name}")
        create_or_update_user_secret(ssm, ssm_param_name, user_secret_string, event)
