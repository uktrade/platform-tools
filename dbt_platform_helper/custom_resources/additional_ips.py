import json
import logging
import time
from urllib import request
from urllib.error import HTTPError

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
    request_type = event["RequestType"]
    try:
        send_response(event, context, "SUCCESS", f"{request_type}d")
    except ClientError as ex:
        send_response(event, context, "FAILED", f"{ex}")
