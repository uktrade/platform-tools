import boto3


class KMSProvider:
    """A provider class for interacting with the AWS KMS (Key Management
    Service)."""

    def __init__(self, kms_client: boto3.client):
        self.kms_client = kms_client

    def describe_key(self, alias_name: str) -> dict:
        """
        Retrieves metadata about a KMS key using its alias.

        Args:
            alias_name (str): The alias name of the KMS key.

        Returns:
            dict: A dictionary containing metadata about the specified KMS key.
        """
        # The kms client can take an alias name as the KeyId
        return self.kms_client.describe_key(KeyId=alias_name)
