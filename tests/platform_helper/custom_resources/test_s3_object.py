import json
import logging
import unittest
from io import BytesIO
from unittest.mock import MagicMock
from unittest.mock import call
from unittest.mock import patch
from urllib.error import HTTPError

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws
from parameterized import parameterized

from dbt_platform_helper.custom_resources import s3_object
from dbt_platform_helper.custom_resources.s3_object import handler


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

        self._event = {
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

        event = self._event.copy()
        event["ResourceProperties"] = with_missing_keys
        handler(event, {})
        sent_request = urlopen.call_args_list[0].args[0]
        sent_body = json.loads(sent_request.data.decode())

        self.assertEqual("https://example.com/cf-response", sent_request.full_url)
        self.assertEqual("FAILED", sent_body["Status"])
        self.assertEqual(f"Missing required properties: {missing_properties}", sent_body["Reason"])

    @patch("time.sleep", return_value=None)
    @patch(
        "urllib.request.urlopen",
        side_effect=HTTPError("https://example.com", 404, "Not Found", None, BytesIO(b"Some Data")),
    )
    def test_failure_to_update_resource_status_retries_5_times(self, urlopen, sleep):
        logger = logging.getLogger(s3_object.__name__)
        logger.warning = MagicMock(logger.warning)
        logger.error = MagicMock(logger.error)

        with_missing_keys = self._resource_properties.copy()
        del with_missing_keys["S3Bucket"]

        event = self._event.copy()
        event["ResourceProperties"] = with_missing_keys
        handler(event, {})

        self.assertEqual(5, urlopen.call_count)
        logger.warning.assert_has_calls(
            [
                call("HTTP Error 404: Not Found [https://example.com] - Retry 1"),
                call("HTTP Error 404: Not Found [https://example.com] - Retry 2"),
                call("HTTP Error 404: Not Found [https://example.com] - Retry 3"),
                call("HTTP Error 404: Not Found [https://example.com] - Retry 4"),
            ]
        )
        logger.error.assert_called_with("HTTP Error 404: Not Found [https://example.com]")
        sleep.assert_has_calls(
            [
                call(5),
                call(10),
                call(15),
                call(20),
            ]
        )

    @parameterized.expand([("Create",), ("Update",)])
    @patch("urllib.request.urlopen", return_value=None)
    @mock_aws
    def test_resource_creation_puts_an_object_in_s3_and_reports_success(
        self, request_type, urlopen
    ):
        s3_client = boto3.client("s3", "eu-west-2")
        event = self._event.copy()
        event["RequestType"] = request_type

        bucket = self._resource_properties["S3Bucket"]
        key = self._resource_properties["S3ObjectKey"]
        s3_client.create_bucket(
            Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
        )

        handler(event, {})

        act_object = s3_client.get_object(Bucket=bucket, Key=key)["Body"].read()
        sent_request = urlopen.call_args_list[0].args[0]
        sent_body = json.loads(sent_request.data.decode())

        self.assertEqual(act_object, self._resource_properties["S3ObjectBody"].encode("utf-8"))
        self.assertEqual("https://example.com/cf-response", sent_request.full_url)
        self.assertEqual("SUCCESS", sent_body["Status"])
        self.assertEqual(f"{request_type}d", sent_body["Reason"])
        self.assertEqual(f"s3://bucket-name/object-with-contents", sent_body["PhysicalResourceId"])

    @patch("urllib.request.urlopen", return_value=None)
    @mock_aws
    def test_resource_delete_removes_an_object_from_s3_and_reports_success(self, urlopen):
        s3_client = boto3.client("s3", "eu-west-2")
        bucket = self._resource_properties["S3Bucket"]
        key = self._resource_properties["S3ObjectKey"]
        s3_client.create_bucket(
            Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
        )
        s3_client.put_object(
            Bucket=self._resource_properties["S3Bucket"],
            Key=self._resource_properties["S3ObjectKey"],
            Body=self._resource_properties["S3ObjectBody"].encode("utf-8"),
        )
        event = self._event.copy()
        event["RequestType"] = "Delete"

        handler(event, {})

        sent_request = urlopen.call_args_list[0].args[0]
        sent_body = json.loads(sent_request.data.decode())

        with pytest.raises(ClientError) as ex:
            s3_client.get_object(Bucket=bucket, Key=key)

        self.assertEqual("NoSuchKey", ex.value.response["Error"]["Code"])
        self.assertEqual("https://example.com/cf-response", sent_request.full_url)
        self.assertEqual("SUCCESS", sent_body["Status"])
        self.assertEqual("Deleted", sent_body["Reason"])
        self.assertEqual(f"s3://bucket-name/object-with-contents", sent_body["PhysicalResourceId"])

    @parameterized.expand([("Create", "Put"), ("Update", "Put"), ("Delete", "Delete")])
    @patch("urllib.request.urlopen", return_value=None)
    @mock_aws
    def test_resource_action_failure_reports_failure(self, request_type, request_action, urlopen):
        event = self._event.copy()
        event["RequestType"] = request_type

        handler(event, {})

        sent_request = urlopen.call_args_list[0].args[0]
        sent_body = json.loads(sent_request.data.decode())

        self.assertEqual("https://example.com/cf-response", sent_request.full_url)
        self.assertEqual("FAILED", sent_body["Status"])
        self.assertEqual(
            f"An error occurred (NoSuchBucket) when calling the {request_action}Object operation: "
            "The specified bucket does not exist",
            sent_body["Reason"],
        )
        self.assertEqual(f"s3://bucket-name/object-with-contents", sent_body["PhysicalResourceId"])


if __name__ == "__main__":
    unittest.main()
