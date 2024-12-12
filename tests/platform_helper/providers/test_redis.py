from unittest.mock import MagicMock

import pytest

from dbt_platform_helper.providers.redis import RedisProvider


# TODO - we don't want to use the fixtures from conftest since one applies get_supported_redis_versions
# However we will remove that autoused fixture once the validation stuff is moved to ConfigProvider, so this line needs to go too.
@pytest.mark.skip_redis_fixture
def test_get_supported_redis_versions_when_cache_refresh_required():

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

    mock_cache_provider = MagicMock()
    mock_cache_provider.cache_refresh_required.return_value = True
    redis_provider._RedisProvider__get_cache_provider = MagicMock(return_value=mock_cache_provider)

    supported_redis_versions_response = redis_provider.get_supported_redis_versions()

    mock_cache_provider.cache_refresh_required.assert_called_with("redis")
    elasticache_client.describe_cache_engine_versions.assert_called_with(Engine="redis")
    mock_cache_provider.update_cache.assert_called_with("redis", ["4.0.10", "5.0.6"])
    assert supported_redis_versions_response == ["4.0.10", "5.0.6"]
