import boto3


class Redis:

    def __init__(self, client: boto3.client):
        self.client = client
        self.engine = "redis"

    def get_reference(self) -> str:
        return self.engine.lower()

    def get_supported_versions(self) -> list[str]:
        supported_versions_response = self.client.describe_cache_engine_versions(Engine=self.engine)

        supported_versions = [
            version["EngineVersion"]
            for version in supported_versions_response["CacheEngineVersions"]
        ]

        return supported_versions
