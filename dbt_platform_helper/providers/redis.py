from dbt_platform_helper.providers.cache import CacheProvider


class RedisProvider:
    def __init__(self, elasticache_client):
        self.elasticache_client = elasticache_client

    def get_supported_redis_versions(self):

        cache_provider = self.__get_cache_provider()

        if cache_provider.cache_refresh_required("redis"):

            supported_versions_response = self.elasticache_client.describe_cache_engine_versions(
                Engine="redis"
            )

            supported_versions = [
                version["EngineVersion"]
                for version in supported_versions_response["CacheEngineVersions"]
            ]

            cache_provider.update_cache("redis", supported_versions)

            return supported_versions

        else:
            return cache_provider.read_supported_versions_from_cache("redis")

    # TODO - cache provider instantiated here rather than via dependancy injection since it will likely only be used in the get_supported_redis_versions method.
    # If another method is added which needs a CacheProvider, it should be injected into the constructor instead.
    @staticmethod
    def __get_cache_provider():
        return CacheProvider()
