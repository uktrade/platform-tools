from dbt_platform_helper.providers.aws import get_reference
from dbt_platform_helper.providers.aws import get_supported_versions
from dbt_platform_helper.providers.aws.interfaces import GetReferenceProtocol
from dbt_platform_helper.providers.aws.interfaces import GetVersionsProtocol
from dbt_platform_helper.providers.cache import CacheProvider


def get_supported_aws_versions(
    client_provider: (
        GetReferenceProtocol | GetVersionsProtocol
    ),  # TODO how to interface required functions of object
    cache_provider=CacheProvider(),
) -> list[str]:
    """
    For a given AWS client provider get the supported versions if the operation
    is supported.

    The cache value is retrieved if it exists.
    """
    supported_versions = []
    aws_reference = get_reference(client_provider)
    if cache_provider.cache_refresh_required(aws_reference):
        supported_versions = get_supported_versions(client_provider)
        cache_provider.update_cache(aws_reference, supported_versions)
    else:
        supported_versions = cache_provider.read_supported_versions_from_cache(aws_reference)

    return supported_versions
