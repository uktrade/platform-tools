import json
import logging
import time
from urllib import request
from urllib.error import HTTPError

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def send_response(event, context, status, message):
    bucket = event["ResourceProperties"].get("S3Bucket", "")
    key = event["ResourceProperties"].get("S3ObjectKey", "")

    body = json.dumps(
        {
            "Status": status,
            "Reason": message,
            "StackId": event["StackId"],
            "RequestId": event["RequestId"],
            "LogicalResourceId": event["LogicalResourceId"],
            "PhysicalResourceId": f"s3://{bucket}/{key}",
            "Data": {
                "Bucket": bucket,
                "Key": key,
            },
        }
    ).encode()

    send = request.Request(event["ResponseURL"], data=body)
    send.get_method = lambda: "PUT"

    count = 0
    while count < 5:
        count += 1
        try:
            request.urlopen(send)
            break
        except HTTPError as ex:
            if count < 5:
                logger.warning(f"{ex} [{ex.url}] - Retry {count}")
            else:
                logger.error(f"{ex} [{ex.url}]")
            time.sleep(count * 5)


def handler(event, context):
    s3_client = boto3.client("s3")
    request_type = event["RequestType"]
    properties = event["ResourceProperties"]
    required_properties = [
        "CopilotApplication",
        "CopilotEnvironment",
        "S3Bucket",
        "S3ObjectBody",
        "S3ObjectKey",
    ]
    missing_properties = [p for p in required_properties if p not in properties]

    if missing_properties:
        missing_properties.sort()
        return send_response(
            event, context, "FAILED", f"Missing required properties: {missing_properties}"
        )

    try:
        if request_type == "Delete":
            s3_client.delete_object(
                Bucket=properties["S3Bucket"],
                Key=properties["S3ObjectKey"],
            )
        else:
            s3_client.put_object(
                Bucket=properties["S3Bucket"],
                Key=properties["S3ObjectKey"],
                Body=properties["S3ObjectBody"].encode("utf-8"),
            )

        send_response(event, context, "SUCCESS", f"{request_type}d")
    except ClientError as ex:
        send_response(event, context, "FAILED", f"{ex}")
