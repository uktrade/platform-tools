from datetime import datetime
from datetime import timedelta
from unittest.mock import MagicMock

from unittest.mock import patch

from dbt_platform_helper.providers.cache import CacheProvider


def test_cache_refresh_required_with_cached_datetime_greater_than_one_day_returns_true():

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

    with patch("dbt_platform_helper.providers.cache.os.path.exists", return_value=True):

        assert cache_provider.cache_refresh_required("redis")


def test_cache_refresh_required_with_cached_datetime_greater_less_one_day_returns_false():

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

    with patch("dbt_platform_helper.providers.cache.os.path.exists", return_value=True):
        assert not cache_provider.cache_refresh_required("redis")


# def test_write_to_cache():

#     today = datetime.now()
#     cache_provider = CacheProvider()

#     read_yaml_return_value = {
#         "redis": {"date-retrieved": today.strftime("%d-%m-%y %H:%M:%S")}
#     }
#     cache_provider._CacheProvider__read_file_as_yaml = MagicMock(
#         return_value=read_yaml_return_value
#     )

#     product = "redis"
#     supported_versions = ["7.1", "7.2"]




