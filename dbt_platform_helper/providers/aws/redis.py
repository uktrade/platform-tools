import boto3


class RedisProvider:

    def __init__(self, client: boto3.client):
        self.client = client
        self.engine = "redis"

    def __get_reference__(self) -> str:
        return self.engine.lower()

    def __get_supported_versions__(self) -> list[str]:
        supported_versions_response = self.client.describe_cache_engine_versions(Engine=self.engine)

        supported_versions = [
            version["EngineVersion"]
            for version in supported_versions_response["CacheEngineVersions"]
        ]

        return supported_versions
