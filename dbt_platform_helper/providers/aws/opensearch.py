import boto3


class Opensearch:

    def __init__(self, client: boto3.client):
        self.client = client
        # TODO extract engine so you could swap between opensearch and elastic in the same provider
        self.engine = "OpenSearch"

    def get_reference(self) -> str:
        return self.engine.lower()

    def get_supported_versions(self) -> list[str]:
        response = self.client.list_versions()
        all_versions = response["Versions"]

        opensearch_versions = [
            version for version in all_versions if version.startswith(f"{self.engine}_")
        ]
        supported_versions = [
            version.removeprefix(f"{self.engine}_") for version in opensearch_versions
        ]

        return supported_versions
