from unittest.mock import MagicMock

import pytest

from dbt_platform_helper.providers.aws import get_reference
from dbt_platform_helper.providers.aws import get_supported_versions


def test_get_reference_raises_attribute_exception():
    mock_aws_provider = MagicMock()
    with pytest.raises(
        AttributeError, match="Object of type MagicMock does not support get_reference"
    ):
        get_reference(mock_aws_provider)


def test_get_reference():
    mock_aws_provider = MagicMock()
    setattr(mock_aws_provider, "__get_reference__", MagicMock(return_value="doesnt-matter"))
    assert "doesnt-matter" == get_reference(mock_aws_provider)


def test_get_supported_versions():
    mock_aws_provider = MagicMock()
    setattr(
        mock_aws_provider,
        "__get_supported_versions__",
        MagicMock(return_value=["doesnt", "matter"]),
    )
    assert ["doesnt", "matter"] == get_supported_versions(mock_aws_provider)


def test_get_supported_versions_raises_attribute_exception():
    mock_aws_provider = MagicMock()
    with pytest.raises(
        Exception, match="Object of type MagicMock does not support get_supported_versions"
    ):
        get_supported_versions(mock_aws_provider)
