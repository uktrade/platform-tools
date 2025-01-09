from unittest.mock import MagicMock

from dbt_platform_helper.domain.versions import get_supported_aws_versions


def test_get_supported_versions_cache_refresh():
    mock_cache_provider = MagicMock()
    mock_aws_provider = MagicMock()
    setattr(mock_aws_provider, "__get_reference__", MagicMock(return_value="doesnt-matter"))
    setattr(
        mock_aws_provider,
        "__get_supported_versions__",
        MagicMock(return_value=["doesnt", "matter"]),
    )
    mock_cache_provider.cache_refresh_required.return_value = True

    versions = get_supported_aws_versions(mock_aws_provider, mock_cache_provider)

    mock_aws_provider.__get_reference__.assert_called()
    mock_aws_provider.__get_supported_versions__.assert_called()
    mock_cache_provider.update_cache.assert_called_with("doesnt-matter", ["doesnt", "matter"])
    mock_cache_provider.read_supported_versions_from_cache.assert_not_called()

    assert versions == ["doesnt", "matter"]


def test_get_supported_versions_no_cache_refresh():
    mock_cache_provider = MagicMock()
    mock_aws_provider = MagicMock()
    setattr(mock_aws_provider, "__get_reference__", MagicMock(return_value="doesnt-matter"))
    setattr(
        mock_aws_provider,
        "__get_supported_versions__",
        MagicMock(return_value=["doesnt", "matter"]),
    )
    mock_cache_provider.cache_refresh_required.return_value = False
    mock_cache_provider.read_supported_versions_from_cache.return_value = [
        "cache",
        "doesnt",
        "matter",
    ]

    versions = get_supported_aws_versions(mock_aws_provider, mock_cache_provider)

    mock_aws_provider.__get_reference__.assert_called()
    mock_aws_provider.__get_supported_versions__.assert_not_called()
    mock_cache_provider.update_cache.assert_not_called()
    mock_cache_provider.read_supported_versions_from_cache.assert_called_with("doesnt-matter")

    assert versions == ["cache", "doesnt", "matter"]
