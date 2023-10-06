import json
from urllib import request
from urllib.error import HTTPError

import boto3

s3_client = boto3.client("s3")

# Initial code taken from "https://github.com/awslabs/aws-cloudformation-templates/blob
# /a11722da8379dd52726ecfcd552f7983e9bb563f/aws/services/CloudFormation/MacrosExamples/S3Objects
# /lambda/resource.py"


def send_response(event, context, status, message):
    bucket = event["ResourceProperties"].get("Target", {}).get("Bucket")
    key = event["ResourceProperties"].get("Target", {}).get("Key")

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
        except HTTPError:
            pass

    # request = Request(, data=body)
    # request.add_header('Content-Type', '')
    # request.add_header('Content-Length', str(len(body)))
    # request.get_method = lambda: 'PUT'
    #
    # opener = build_opener(HTTPHandler)
    # opener.open(request)


def handler(event, context):
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

    # if "Target" not in properties or all(prop not in properties for prop in ["Body", "Base64Body", "Source"]):
    #     return sendResponse(event, context, "FAILED", "Missing required parameters")
    #
    # target = properties["Target"]
    #
    # if request in ("Create", "Update"):
    #     if "Body" in properties:
    #         target.update({
    #             "Body": properties["Body"],
    #         })
    #
    #         s3_client.put_object(**target)
    #
    #     elif "Base64Body" in properties:
    #         try:
    #             body = base64.b64decode(properties["Base64Body"])
    #         except:
    #             return sendResponse(event, context, "FAILED", "Malformed Base64Body")
    #
    #         target.update({
    #             "Body": body
    #         })
    #
    #         s3_client.put_object(**target)
    #
    #     elif "Source" in properties:
    #         source = properties["Source"]
    #
    #         s3_client.copy_object(
    #             CopySource=source,
    #             Bucket=target["Bucket"],
    #             Key=target["Key"],
    #             MetadataDirective="COPY",
    #             TaggingDirective="COPY",
    #             ACL=target["ACL"],
    #         )
    #
    #     else:
    #         return sendResponse(event, context, "FAILED", "Malformed body")
    #
    #     return sendResponse(event, context, "SUCCESS", "Created")
    #
    # if request == "Delete":
    #     s3_client.delete_object(
    #         Bucket=target["Bucket"],
    #         Key=target["Key"],
    #     )
    #
    #     return sendResponse(event, context, "SUCCESS", "Deleted")
    #
    # return sendResponse(event, context, "FAILED", "Unexpected: {}".format(request))
