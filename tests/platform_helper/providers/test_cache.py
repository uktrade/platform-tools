import os
from datetime import datetime
from datetime import timedelta
from unittest.mock import MagicMock

from dbt_platform_helper.providers.cache import CacheProvider


def test_cache_refresh_required_is_true_when_cached_datetime_greater_than_one_day():

    cache_provider = CacheProvider()

    read_yaml_return_value = {
        "redis": {
            # Some timestamp which is > than 1 day. i.e. enough to trigger a cache refresh
            "date-retrieved": "09-02-02 10:35:48"
        }
    }
    cache_provider._CacheProvider__read_file_as_yaml = MagicMock(
        return_value=read_yaml_return_value
    )
    os.path.exists = MagicMock(return_value=True)

    assert cache_provider.cache_refresh_required("redis")


def test_cache_refresh_required_is_false_when_cached_datetime_less_than_one_day():

    today = datetime.now()
    # Time range is still < 1 day so should not require refresh
    middle_of_today = today - timedelta(hours=12)

    cache_provider = CacheProvider()

    read_yaml_return_value = {
        "redis": {"date-retrieved": middle_of_today.strftime("%d-%m-%y %H:%M:%S")}
    }
    cache_provider._CacheProvider__read_file_as_yaml = MagicMock(
        return_value=read_yaml_return_value
    )
    os.path.exists = MagicMock(return_value=True)

    assert not cache_provider.cache_refresh_required("redis")
