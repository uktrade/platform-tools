import json
import unittest
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

from parameterized import parameterized

from dbt_copilot_helper.custom_resources.s3_object import handler


class TestS3ObjectCustomResource(unittest.TestCase):
    def setUp(self):
        self._resource_properties = {
            "Name": "app-test-s3-objects",
            "CopilotApplication": "app",
            "CopilotEnvironment": "test",
            "S3Bucket": "bucket-name",
            "S3ObjectKey": "object-with-contents",
            "S3ObjectBody": "test content",
        }

        self._create_event = {
            "RequestType": "Create",
            "LogicalResourceId": "servicePrefixS3Object0",
            "StackId": "1906d5fb-e2b3-426c-b308-14dd13efd918",
            "RequestId": "ccccb225-37f6-4959-bedb-f0cc8502a95f",
            "ResponseURL": "https://example.com/cf-response",
            "ResourceProperties": self._resource_properties,
        }

    @parameterized.expand(
        [
            (["CopilotApplication"],),
            (["CopilotEnvironment"],),
            (["S3Bucket"],),
            (["S3ObjectKey"],),
            (["S3ObjectBody"],),
            (["CopilotApplication", "CopilotEnvironment"],),
            (["S3Bucket", "S3ObjectKey", "S3ObjectBody"],),
            (
                [
                    "CopilotApplication",
                    "CopilotEnvironment",
                    "S3Bucket",
                    "S3ObjectKey",
                    "S3ObjectBody",
                ],
            ),
        ]
    )
    @patch("urllib.request.urlopen", return_value=None)
    def test_creating_an_object_without_required_parameters_sends_failure_status(
        self, missing_properties, urlopen
    ):
        with_missing_keys = self._resource_properties.copy()
        missing_properties.sort()

        for missing_key in missing_properties:
            del with_missing_keys[missing_key]

        event = self._create_event.copy()
        event["ResourceProperties"] = with_missing_keys
        handler(event, {})
        sent_request = urlopen.call_args_list[0].args[0]
        sent_body = json.loads(sent_request.data.decode())

        self.assertEqual("https://example.com/cf-response", sent_request.full_url)
        self.assertEqual("FAILED", sent_body["Status"])
        self.assertEqual(f"Missing required properties: {missing_properties}", sent_body["Reason"])

    @patch(
        "urllib.request.urlopen",
        side_effect=HTTPError("https://example.com", 404, "Not Found", None, BytesIO(b"Some Data")),
    )
    def test_failure_to_update_resource_status_retries_5_times(self, urlopen):
        with_missing_keys = self._resource_properties.copy()
        del with_missing_keys["S3Bucket"]

        event = self._create_event.copy()
        event["ResourceProperties"] = with_missing_keys
        handler(event, {})

        self.assertEqual(5, urlopen.call_count)


if __name__ == "__main__":
    unittest.main()
