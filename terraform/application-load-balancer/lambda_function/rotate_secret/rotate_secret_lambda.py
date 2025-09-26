import logging

import boto3
from secret_rotator import SecretRotator

logger = logging.getLogger()
logger.setLevel(logging.INFO)

service_client = boto3.client("secretsmanager")


def lambda_handler(event, context):
    secret_id = event.get("SecretId")
    step = event.get("Step")
    token = event.get("ClientRequestToken")

    if not secret_id:
        logger.error("Unable to determine SecretId.")
        raise ValueError("Unable to determine SecretId.")

    rotator = SecretRotator(logger=logger)

    if step == "createSecret":
        logger.info("Entered createSecret step")
        rotator.create_secret(service_client, secret_id, token)
    elif step == "setSecret":
        logger.info("Entered setSecret step")
        rotator.set_secret(service_client, secret_id, token)
    elif step == "testSecret":
        logger.info("Entered testSecret step")
        rotator.run_test_secret(service_client, secret_id, token, event.get("TestDomains", []))
    elif step == "finishSecret":
        logger.info("Entered finishSecret step")
        rotator.finish_secret(service_client, secret_id, token)
    else:
        logger.error(f"Invalid step parameter: {step}")
        raise ValueError(f"Invalid step parameter: {step}")
