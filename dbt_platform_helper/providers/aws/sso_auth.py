import botocore
from boto3 import Session

from dbt_platform_helper.providers.aws.exceptions import CreateAccessTokenException
from dbt_platform_helper.utils.aws import get_aws_session_or_abort


class SSOAuthProvider:
    def __init__(self, session: Session = None):
        self.session = session
        self.sso_oidc = self._get_client("sso-oidc")
        self.sso = self._get_client("sso")

    def register(self, client_name, client_type):
        client = self.sso_oidc.register_client(clientName=client_name, clientType=client_type)
        client_id = client.get("clientId")
        client_secret = client.get("clientSecret")

        return client_id, client_secret

    def start_device_authorization(self, client_id, client_secret, start_url):
        authz = self.sso_oidc.start_device_authorization(
            client_id=client_id,
            client_secret=client_secret,
            start_url=start_url,
        )
        url = authz.get("verificationUriComplete")
        deviceCode = authz.get("deviceCode")

        return url, deviceCode

    def create_access_token(self, client_id, client_secret, device_code):
        try:
            access_token = self.sso_oidc.create_access_token(
                client_id=client_id,
                client_secret=client_secret,
                grant_type="urn:ietf:params:oauth:grant-type:device_code",
                device_code=device_code,
            )

            return access_token

        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "AuthorizationPendingException":
                raise CreateAccessTokenException(client_id)

    def list_accounts(self, access_token, max_results=100):
        aws_accounts_response = self.sso.list_accounts(
            accessToken=access_token,
            maxResults=max_results,
        )

        if len(aws_accounts_response.get("accountList", [])) == 0:
            raise RuntimeError("Unable to retrieve AWS SSO account list\n")
        return aws_accounts_response.get("accountList")

    def _get_client(self, client: str):
        if not self.session:
            self.session = get_aws_session_or_abort()
        return self.session.client(client)
