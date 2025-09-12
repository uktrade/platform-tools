import boto3
from botocore.exceptions import ClientError

from dbt_platform_helper.platform_exception import PlatformException


class S3Provider:

    def __init__(self, client: boto3.client = None):
        self.client = client or boto3.client("s3")

    def get_object(self, bucket_name: str, object_key: str) -> str:
        """Returns an object from an S3 bucket."""

        try:
            content = self.client.get_object(Bucket=bucket_name, Key=object_key)
            return content["Body"].read().decode("utf-8")
        except ClientError as e:
            raise PlatformException(
                f"Failed to get '{object_key}' from '{bucket_name}'. Error: {e}"
            )
