from boto3 import Session

from dbt_platform_helper.utils.aws import get_aws_session_or_abort


class SSOAuthProvider:
    def __init__(self, session: Session = None):
        self.session = session
        self.sso_oidc = self._get_client("sso-oidc")

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

    def create_access_token(self, client_id, client_secret, grant_type, device_code):
        pass

    def list_accounts(self, access_token, max_results):
        pass

    def _get_client(self, client: str):
        if not self.session:
            self.session = get_aws_session_or_abort()
        return self.session.client(client)
