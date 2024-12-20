from dbt_platform_helper.providers.aws.exceptions import InvalidAWSClient
from dbt_platform_helper.providers.aws.interfaces import ClientProvider
from dbt_platform_helper.providers.aws.opensearch import OpensearchProviderV2
from dbt_platform_helper.providers.aws.redis import RedisProviderV2


# TODO think of a way of stubbing ClientProvider's to improve testing and local development.
def get_client_provider(client: str) -> ClientProvider:
    if client == "elasticache":
        return RedisProviderV2()
    elif client == "opensearch":
        return OpensearchProviderV2()
    else:
        raise InvalidAWSClient(client)
