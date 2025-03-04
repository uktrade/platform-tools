from datetime import datetime
from datetime import timedelta
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from freezegun import freeze_time

from dbt_platform_helper.providers.cache import Cache
from dbt_platform_helper.providers.cache import GetAWSVersionStrategy


@freeze_time("2024-12-09 16:00:00")
def test_update_cache_when_cache_exists():
    file_provider_mock = MagicMock()
    cache_provider = Cache(file_provider=file_provider_mock)

    read_yaml_return_value = {
        "redis": {"date-retrieved": "09-02-02 10:35:48", "versions": ["7.1", "7.2"]}
    }
    file_provider_mock.load.return_value = read_yaml_return_value
    file_provider_mock.write = MagicMock()

    expected_contents = {
        "redis": {"date-retrieved": "09-02-02 10:35:48", "versions": ["7.1", "7.2"]},
        "opensearch": {"versions": ["6.1", "6.2"], "date-retrieved": "09-12-24 16:00:00"},
    }

    with patch("dbt_platform_helper.providers.cache.os.path.exists", return_value=True):

        cache_provider._update_cache("opensearch", ["6.1", "6.2"])

    file_provider_mock.write.assert_called_once_with(
        ".platform-helper-config-cache.yml",
        expected_contents,
        "# [!] This file is autogenerated via the platform-helper. Do not edit.\n",
    )


def test_read_supported_versions_from_cache_when_resource_exists():
    file_provider_mock = MagicMock()
    cache_provider = Cache(file_provider=file_provider_mock)

    read_yaml_return_value = {
        "redis": {"date-retrieved": "09-02-02 10:35:48", "versions": ["7.1", "7.2"]},
        "opensearch": {"date-retrieved": "09-02-02 10:35:48", "versions": ["6.1", "6.2"]},
    }
    file_provider_mock.load.return_value = read_yaml_return_value

    supported_versions = cache_provider._read_from_cache("opensearch")

    assert supported_versions == ["6.1", "6.2"]


def test_cache_refresh_required_when_cache_file_does_not_exist():
    file_provider_mock = MagicMock()
    cache_provider = Cache(file_provider=file_provider_mock)

    file_provider_mock.load.side_effect = FileNotFoundError

    result = cache_provider._cache_refresh_required("opensearch")

    assert result is True


def test_cache_refresh_required_when_resource_name_does_not_exist_in_cache():
    file_provider_mock = MagicMock()
    cache_provider = Cache(file_provider=file_provider_mock)

    read_yaml_return_value = {
        "redis": {"date-retrieved": "01-01-01 10:00:00", "versions": ["7.1", "7.2"]},
    }
    file_provider_mock.load.return_value = read_yaml_return_value

    result = cache_provider._cache_refresh_required("opensearch")

    assert result is True


def test_cache_refresh_required_when_date_retrieved_is_older_than_one_day():
    file_provider_mock = MagicMock()
    cache_provider = Cache(file_provider=file_provider_mock)

    read_yaml_return_value = {
        "opensearch": {"date-retrieved": "01-01-01 10:00:00", "versions": ["6.1", "6.2"]},
    }
    file_provider_mock.load.return_value = read_yaml_return_value

    cache_provider._CacheProvider__check_if_cached_datetime_is_greater_than_interval = Mock(
        return_value=True
    )

    result = cache_provider._cache_refresh_required("opensearch")

    assert result is True


def test_cache_refresh_not_required_when_cache_is_less_than_one_day_old():
    current_time = datetime.now()
    date_retrieved = (current_time - timedelta(hours=2)).strftime("%d-%m-%y %H:%M:%S")

    file_provider_mock = MagicMock()
    cache_provider = Cache(file_provider=file_provider_mock)
    file_provider_mock.load.return_value = {"opensearch": {"date-retrieved": date_retrieved}}

    cache_provider._Cache__cache_exists = Mock(return_value=True)

    with freeze_time(current_time):
        assert not cache_provider._cache_refresh_required("opensearch")


@pytest.mark.skip_mock_get_data
def test_get_data():
    file_provider_mock = MagicMock()
    cache_provider = Cache(file_provider=file_provider_mock)
    strategy = MagicMock()
    strategy.get_resource_identifier.return_value = "doesnt-matter"
    strategy.retrieve_fresh_data.return_value = ["this", "no", "matter"]

    cache_provider._cache_refresh_required = MagicMock()
    cache_provider._cache_refresh_required.return_value = True
    cache_provider._read_from_cache = MagicMock()
    cache_provider._update_cache = MagicMock()

    retrieved_data = cache_provider.get_data(strategy)

    assert retrieved_data == ["this", "no", "matter"]
    cache_provider._cache_refresh_required.assert_called_with("doesnt-matter")
    cache_provider._update_cache.assert_called_with("doesnt-matter", ["this", "no", "matter"])
    cache_provider._read_from_cache.assert_not_called()


@pytest.mark.skip_mock_get_data
def test_get_data_no_cache_refresh():
    file_provider_mock = MagicMock()
    cache_provider = Cache(file_provider=file_provider_mock)
    strategy = MagicMock()
    strategy.get_resource_identifier.return_value = "doesnt-matter"
    strategy.retrieve_fresh_data.return_value = ["this", "no", "matter"]

    cache_provider._cache_refresh_required = MagicMock()
    cache_provider._cache_refresh_required.return_value = False
    cache_provider._read_from_cache = MagicMock()
    cache_provider._read_from_cache.return_value = [
        "cache",
        "doesnt",
        "matter",
    ]
    cache_provider._update_cache = MagicMock()

    retrieved_data = cache_provider.get_data(strategy)

    cache_provider._cache_refresh_required.assert_called_with("doesnt-matter")
    cache_provider._update_cache.assert_not_called()
    cache_provider._read_from_cache.assert_called_with("doesnt-matter")

    assert retrieved_data == ["cache", "doesnt", "matter"]


def test_get_aws_version_strategy():
    client_proivder = MagicMock()
    client_proivder.get_supported_versions.return_value = ["doesnt", "matter"]
    client_proivder.get_reference.return_value = "doesnt-matter"

    strategy = GetAWSVersionStrategy(client_proivder)

    assert strategy.retrieve_fresh_data() == ["doesnt", "matter"]
    assert strategy.get_resource_identifier() == "doesnt-matter"
