from unittest.mock import MagicMock
from unittest.mock import call
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.logs import LogsProvider


def test_check_log_streams_present_success():
    mock_logs = MagicMock()

    # Returns the requests log streams right away
    def _describe_log_streams(**kwargs):
        log_stream_prefix = kwargs["logStreamNamePrefix"]
        return {"logStreams": [{"logStreamName": log_stream_prefix}]}

    mock_logs.describe_log_streams.side_effect = _describe_log_streams

    provider = LogsProvider(client=mock_logs)

    result = provider.check_log_streams_present(
        log_group="/aws/logs/group",
        expected_log_streams=["stream1", "stream2"],
    )

    assert result is True
    mock_logs.describe_log_streams.assert_has_calls(
        [
            call(logGroupName="/aws/logs/group", logStreamNamePrefix="stream1", limit=1),
            call(logGroupName="/aws/logs/group", logStreamNamePrefix="stream2", limit=1),
        ],
        any_order=True,
    )


def _return_client_error(code="ResourceNotFoundException", op="DescribeLogStreams"):
    return ClientError({"Error": {"Code": code, "Message": "boom"}}, op)


def test_check_log_streams_present_raises_exception():
    mock_logs = MagicMock()

    mock_logs.describe_log_streams.side_effect = _return_client_error("Error")

    provider = LogsProvider(client=mock_logs)

    with pytest.raises(PlatformException) as e:
        # Time patch not needed - error gets raised on first check
        provider.check_log_streams_present("/aws/logs/group", ["stream1"])

    assert "Failed to check if log stream 'stream1' exists" in str(e.value)


@patch("dbt_platform_helper.providers.logs.time.sleep", return_value=None)
def test_check_log_streams_present_times_out(_sleep):
    mock_logs = MagicMock()
    # Returns empty, never finds the log streams
    mock_logs.describe_log_streams.return_value = {"logStreams": []}

    provider = LogsProvider(client=mock_logs)

    # Fake time: 0 = deadline starts, 1 = loop once, 301 = timeout and exit
    with patch("dbt_platform_helper.providers.logs.time.monotonic", side_effect=[0, 1, 301]):
        with pytest.raises(PlatformException) as ex:
            provider.check_log_streams_present("/aws/logs/group", ["stream1", "stream2"])

    assert "Timed out waiting for the following log streams to create" in str(ex.value)
