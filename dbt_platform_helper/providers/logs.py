import time
from typing import Any

import boto3
from botocore.exceptions import ClientError

from dbt_platform_helper.platform_exception import PlatformException


class LogsProvider:

    def __init__(self, client: boto3.client):
        self.client = client

    def check_log_streams_present(self, log_group: str, expected_log_streams: list[str]) -> bool:
        """
        Check whether the logs streams provided exist or not.

        Retry for up to 5 minutes.
        """

        found_log_streams = set()
        expected_log_streams = set(expected_log_streams)
        timeout_seconds = 300
        poll_interval_seconds = 2
        deadline_seconds = time.monotonic() + timeout_seconds

        while time.monotonic() < deadline_seconds:

            remaining_log_streams = expected_log_streams - found_log_streams
            if not remaining_log_streams:
                return True

            for log_stream in list(remaining_log_streams):
                try:
                    response = self.client.describe_log_streams(
                        logGroupName=log_group, logStreamNamePrefix=log_stream, limit=1
                    )
                except ClientError as e:
                    code = e.response.get("Error", {}).get("Code")
                    if code == "ResourceNotFoundException":
                        continue  # Log stream not there yet, keep going
                    else:
                        raise PlatformException(
                            f"Failed to check if log stream '{log_stream}' exists due to an error {e}"
                        )

                for ls in response.get("logStreams", []):
                    if ls.get("logStreamName") == log_stream:
                        found_log_streams.add(log_stream)

            if expected_log_streams - found_log_streams:
                time.sleep(poll_interval_seconds)

        missing_log_streams = expected_log_streams - found_log_streams
        raise PlatformException(
            f"Timed out waiting for the following log streams to create: {missing_log_streams}"
        )

    def get_log_stream_events(
        self, log_group: str, log_stream: str, limit: int
    ) -> list[dict[str, Any]]:
        """Return events for a specific log stream."""

        try:
            self.check_log_streams_present(log_group=log_group, expected_log_streams=[log_stream])
            response = self.client.get_log_events(
                logGroupName=log_group, logStreamName=log_stream, limit=limit
            )
            return response["events"]
        except ClientError as err:
            raise PlatformException(f"Error retrieving log stream events: {err}")
