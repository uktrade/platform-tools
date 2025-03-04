from unittest.mock import MagicMock

from dbt_platform_helper.providers.aws.opensearch import Opensearch


def test_opensearch_provider_get_reference():
    opensearch_client = MagicMock()
    opensearch_provider = Opensearch(opensearch_client)

    reference = opensearch_provider.get_reference()

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
    opensearch_provider = Opensearch(opensearch_client)

    supported_opensearch_versions_response = opensearch_provider.get_supported_versions()

    opensearch_client.list_versions.assert_called_with()
    assert supported_opensearch_versions_response == ["2.15", "2.13", "2.11", "2.9"]
