from typing import List

from dbt_platform_helper.providers.aws.interfaces import GetReferenceProtocol
from dbt_platform_helper.providers.aws.interfaces import GetVersionsProtocol
from dbt_platform_helper.providers.cache import CacheProvider


class AwsGetVersionProtocol(GetReferenceProtocol, GetVersionsProtocol):
    pass


# TODO this will be set up within the caching provider using the stragegy pattern
def get_supported_aws_versions(
    client_provider: AwsGetVersionProtocol,
    cache_provider=CacheProvider(),
) -> List[str]:
    """
    For a given AWS client provider get the supported versions if the operation
    is supported.

    The cache value is retrieved if it exists.
    """
    supported_versions = []
    aws_reference = client_provider.get_reference()
    if cache_provider.cache_refresh_required(aws_reference):
        supported_versions = client_provider.get_supported_versions()
        cache_provider.update_cache(aws_reference, supported_versions)
    else:
        supported_versions = cache_provider.read_supported_versions_from_cache(aws_reference)

    return supported_versions
