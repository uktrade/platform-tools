import datetime

import boto3
import botocore
from django.conf import settings

sso_client = boto3.client("sso", region_name=settings.AWS_REGION)
sso_oidc_client = boto3.client("sso-oidc", region_name=settings.AWS_REGION)


def create_oidc_application(sso_oidc_client):
    print("Creating temporary AWS SSO OIDC application")
    client = sso_oidc_client.register_client(
        clientName="pipelines-app",
        clientType="public",
    )
    client_id = client.get("clientId")
    client_secret = client.get("clientSecret")
    breakpoint()
    return client_id, client_secret


def initiate_device_code_flow(oidc_application, start_url):
    print("Initiating device code flow")
    authz = sso_oidc_client.start_device_authorization(
        clientId=oidc_application[0],
        clientSecret=oidc_application[1],
        startUrl=start_url,
    )

    url = authz.get("verificationUriComplete")
    deviceCode = authz.get("deviceCode")
    return url, deviceCode


def create_device_code_url(start_url, oidc_application=None):
    if not oidc_application:
        oidc_application = create_oidc_application(sso_oidc_client)
    url, device_code = initiate_device_code_flow(
        oidc_application,
        start_url,
    )
    return url, device_code, oidc_application


def retrieve_aws_accounts(aws_sso_token):
    aws_accounts_response = sso_client.list_accounts(
        accessToken=aws_sso_token,
        maxResults=100,
    )
    if len(aws_accounts_response.get("accountList", [])) == 0:
        raise RuntimeError("Unable to retrieve AWS SSO account list\n")
    return aws_accounts_response.get("accountList")


def retrieve_roles_in_account(aws_sso_token, account_id):
    roles_response = sso_client.list_account_roles(
        accessToken=aws_sso_token,
        accountId=account_id,
    )
    if len(roles_response.get("roleList", [])) == 0:
        raise RuntimeError(f"Unable to retrieve roles in account {account_id}\n")

    return [role.get("roleName") for role in roles_response.get("roleList")]


def retrieve_credentials(aws_sso_token, account_id, role_name):
    sts_creds = sso_client.get_role_credentials(
        accessToken=aws_sso_token,
        roleName=role_name,
        accountId=account_id,
    )

    if "roleCredentials" not in sts_creds:
        raise RuntimeError("Unable to retrieve STS credentials")
    credentials = sts_creds.get("roleCredentials")
    if "accessKeyId" not in credentials:
        raise RuntimeError("Unable to retrieve STS credentials")

    return {
        "aws_access_key_id": credentials["accessKeyId"],
        "aws_secret_access_key": credentials["secretAccessKey"],
        "aws_session_token": credentials["sessionToken"],
        "expiration": credentials["expiration"],
        "role": role_name,
    }


def get_access_token(device_code):
    client_id, secret_key = settings.AWS_OIDC_APP

    try:
        token_response = sso_oidc_client.create_token(
            clientId=client_id,
            clientSecret=secret_key,
            grantType="urn:ietf:params:oauth:grant-type:device_code",
            deviceCode=device_code,
        )

        # renew 60 seconds earlier to avoid the token being expired
        expires = datetime.datetime.now().timestamp() + token_response["expiresIn"] - 60

        return {
            "token": token_response.get("accessToken"),
            "expires": expires,
        }

    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] != "AuthorizationPendingException":
            raise e
