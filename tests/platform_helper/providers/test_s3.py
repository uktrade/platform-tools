from unittest.mock import MagicMock

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.s3 import S3Provider


@mock_aws
def test_get_object_success():
    s3 = boto3.client("s3", region_name="eu-west-2")
    bucket = "my-bucket"
    key = "path/to/file.txt"
    body = "hello world"

    s3.create_bucket(
        Bucket=bucket,
        CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
    )
    s3.put_object(Bucket=bucket, Key=key, Body=body.encode("utf-8"))

    s3_provider = S3Provider(client=s3)

    content = s3_provider.get_object(bucket_name=bucket, object_key=key)

    assert content == body


def _return_client_error(operation="GetObject"):
    return ClientError(
        error_response={"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
        operation_name=operation,
    )


def test_get_object_raises_platform_exception():
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = _return_client_error()

    s3_provider = S3Provider(client=mock_s3)

    with pytest.raises(PlatformException) as e:
        s3_provider.get_object(bucket_name="my-bucket", object_key="missing.txt")

    assert "Failed to get 'missing.txt' from 'my-bucket'." in str(e.value)
    mock_s3.get_object.assert_called_once_with(Bucket="my-bucket", Key="missing.txt")
