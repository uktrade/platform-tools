from unittest.mock import MagicMock

import pytest

from dbt_platform_helper.providers.aws.opensearch import OpensearchProvider
from dbt_platform_helper.providers.aws.opensearch import OpensearchProviderDuck


@pytest.mark.skip_opensearch_fixture
def test_get_supported_opensearch_versions_when_cache_refresh_required():

    opensearch_client = MagicMock()
    opensearch_client.list_versions.return_value = {
        "Versions": [
            "OpenSearch_2.15",
            "OpenSearch_2.13",
            "OpenSearch_2.11",
            "OpenSearch_2.9",
            "Elasticsearch_7.10",
            "Elasticsearch_7.9",
        ]
    }

    opensearch_provider = OpensearchProvider(opensearch_client)

    mock_cache_provider = MagicMock()
    mock_cache_provider.cache_refresh_required.return_value = True
    opensearch_provider._OpensearchProvider__get_cache_provider = MagicMock(
        return_value=mock_cache_provider
    )

    supported_opensearch_versions_response = opensearch_provider.get_supported_opensearch_versions()

    mock_cache_provider.cache_refresh_required.assert_called_with("opensearch")
    opensearch_client.list_versions.assert_called_with()
    mock_cache_provider.update_cache.assert_called_with(
        "opensearch", ["2.15", "2.13", "2.11", "2.9"]
    )
    assert supported_opensearch_versions_response == ["2.15", "2.13", "2.11", "2.9"]


def test_opensearch_provider_get_reference():
    opensearch_client = MagicMock()
    opensearch_provider = OpensearchProviderDuck(opensearch_client)

    reference = opensearch_provider.__get_reference__()

    assert reference == "opensearch"


def test_opensearch_provider_get_supported_versions():

    opensearch_client = MagicMock()
    opensearch_client.list_versions.return_value = {
        "Versions": [
            "OpenSearch_2.15",
            "OpenSearch_2.13",
            "OpenSearch_2.11",
            "OpenSearch_2.9",
            "Elasticsearch_7.10",
            "Elasticsearch_7.9",
        ]
    }
    opensearch_provider = OpensearchProviderDuck(opensearch_client)

    supported_opensearch_versions_response = opensearch_provider.__get_supported_versions__()

    opensearch_client.list_versions.assert_called_with()
    assert supported_opensearch_versions_response == ["2.15", "2.13", "2.11", "2.9"]
