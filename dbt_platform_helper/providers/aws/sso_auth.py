class SSOAuthProvider:
    def __init__(self):
        pass

    def register(self, client_name, client_type):
        pass

    def start_device_authorization(self, client_id, client_secret, start_url):
        pass

    def create_access_token(self, client_id, client_secret, grant_type, device_code):
        pass

    def list_accounts(self, access_token, max_results):
        pass
