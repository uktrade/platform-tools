from dbt_platform_helper.providers.cache import CacheProvider


class OpensearchProvider:

    def __init__(self, opensearch_client):
        self.opensearch_client = opensearch_client

    def get_supported_opensearch_versions(self) -> list[str]:

        cache_provider = self.__get_cache_provider()

        if cache_provider.cache_refresh_required("opensearch"):

            response = self.opensearch_client.list_versions()
            all_versions = response["Versions"]

            opensearch_versions = [
                version for version in all_versions if not version.startswith("Elasticsearch_")
            ]
            supported_versions = [
                version.removeprefix("OpenSearch_") for version in opensearch_versions
            ]

            cache_provider.update_cache("opensearch", supported_versions)

            return supported_versions

        else:
            return cache_provider.read_supported_versions_from_cache("opensearch")

    # TODO - cache provider instantiated here rather than via dependancy injection since it will likely only be used in the get_supported_opensearch_versions method.
    # If another method is added which needs a CacheProvider, it should be injected into the constructor instead.
    @staticmethod
    def __get_cache_provider():
        return CacheProvider()
