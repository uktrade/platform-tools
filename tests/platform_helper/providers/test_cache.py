from datetime import datetime
from datetime import timedelta
from unittest.mock import MagicMock
from unittest.mock import patch

from freezegun import freeze_time

from dbt_platform_helper.providers.cache import CacheProvider


def test_cache_refresh_required_with_cached_datetime_greater_than_one_day_returns_true():

    cache_provider = CacheProvider()

    read_yaml_return_value = {
        "redis": {
            # Some timestamp which is > than 1 day. i.e. enough to trigger a cache refresh
            "date-retrieved": "09-02-02 10:35:48"
        }
    }

    # TODO - read_file_as_yaml mocking will fall away as a result of this functionality being delegated to YamlFiles refactor
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
    # TODO - read_file_as_yaml mocking will fall away as a result of this functionality being delegated to YamlFiles refactor
    cache_provider._CacheProvider__read_file_as_yaml = MagicMock(
        return_value=read_yaml_return_value
    )

    with patch("dbt_platform_helper.providers.cache.os.path.exists", return_value=True):
        assert not cache_provider.cache_refresh_required("redis")


@freeze_time("2024-12-09 16:00:00")
def test_update_cache_with_existing_cache_file_expected_file():

    cache_provider = CacheProvider()

    read_yaml_return_value = {
        "redis": {"date-retrieved": "09-02-02 10:35:48", "versions": ["7.1", "7.2"]}
    }
    # TODO - read_file_as_yaml mocking will fall away as a result of this functionality being delegated to YamlFiles refactor
    cache_provider._CacheProvider__read_file_as_yaml = MagicMock(
        return_value=read_yaml_return_value
    )
    cache_provider._CacheProvider__write_cache = MagicMock()

    expected_contents = {
        "redis": {"date-retrieved": "09-02-02 10:35:48", "versions": ["7.1", "7.2"]},
        "opensearch": {"versions": ["6.1", "6.2"], "date-retrieved": "09-12-24 16:00:00"},
    }

    with patch("dbt_platform_helper.providers.cache.os.path.exists", return_value=True):

        cache_provider.update_cache("opensearch", ["6.1", "6.2"])

    cache_provider._CacheProvider__write_cache.assert_called_once_with(expected_contents)


def test_read_supported_versions_from_cache_returns_correct_product():

    cache_provider = CacheProvider()

    read_yaml_return_value = {
        "redis": {"date-retrieved": "09-02-02 10:35:48", "versions": ["7.1", "7.2"]},
        "opensearch": {"date-retrieved": "09-02-02 10:35:48", "versions": ["6.1", "6.2"]},
    }
    # TODO - read_file_as_yaml mocking will fall away as a result of this functionality being delegated to YamlFiles refactor
    cache_provider._CacheProvider__read_file_as_yaml = MagicMock(
        return_value=read_yaml_return_value
    )

    supported_versions = cache_provider.read_supported_versions_from_cache("opensearch")

    assert supported_versions == ["6.1", "6.2"]
