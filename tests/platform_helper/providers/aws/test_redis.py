from unittest.mock import MagicMock

from dbt_platform_helper.providers.aws.redis import RedisProvider


def test_redis_provider_get_reference():
    elasticache_client = MagicMock()
    redis_provider = RedisProvider(elasticache_client)

    reference = redis_provider.__get_reference__()

    assert reference == "redis"


def test_redis_provider_get_supported_versions():

    elasticache_client = MagicMock()
    elasticache_client.describe_cache_engine_versions.return_value = {
        "CacheEngineVersions": [
            {
                "Engine": "redis",
                "EngineVersion": "4.0.10",
                "CacheParameterGroupFamily": "redis4.0",
                "CacheEngineDescription": "Redis",
                "CacheEngineVersionDescription": "redis version 4.0.10",
            },
            {
                "Engine": "redis",
                "EngineVersion": "5.0.6",
                "CacheParameterGroupFamily": "redis5.0",
                "CacheEngineDescription": "Redis",
                "CacheEngineVersionDescription": "redis version 5.0.6",
            },
        ]
    }

    redis_provider = RedisProvider(elasticache_client)

    supported_versions_response = redis_provider.__get_supported_versions__()

    elasticache_client.describe_cache_engine_versions.assert_called_with(Engine="redis")
    assert supported_versions_response == ["4.0.10", "5.0.6"]
