import json
import urllib

import boto3


class AWSProvider:
    # TODO Unused class probably remove
    def __init__(self, session=boto3.Session()):
        self.session = session
        self.clients = {}

    def register_client(self, service_name):
        if service_name not in self.clients:
            self.clients[service_name] = self.session.client(service_name)

    def get_client(self, service_name):
        if service_name not in self.clients:
            self.register_client(service_name)
        return self.clients[service_name]


class AWSError(Exception):
    pass


class SecretNotFoundError(AWSError):
    pass


def get_postgres_connection_data_updated_with_master_secret(
    ssm_client, secrets_manager_client, parameter_name, secret_arn
):
    # ssm_client = session.client("ssm")
    # secrets_manager_client = session.client("secretsmanager")
    response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
    parameter_value = response["Parameter"]["Value"]

    parameter_data = json.loads(parameter_value)

    secret_response = secrets_manager_client.get_secret_value(SecretId=secret_arn)
    secret_value = json.loads(secret_response["SecretString"])

    parameter_data["username"] = urllib.parse.quote(secret_value["username"])
    parameter_data["password"] = urllib.parse.quote(secret_value["password"])

    return parameter_data


def get_connection_secret_arn(ssm_client, secrets_manager_client, secret_name: str) -> str:

    try:
        return ssm_client.get_parameter(Name=secret_name, WithDecryption=False)["Parameter"]["ARN"]
    except ssm_client.exceptions.ParameterNotFound:
        pass

    try:
        return secrets_manager_client.describe_secret(SecretId=secret_name)["ARN"]
    except secrets_manager_client.exceptions.ResourceNotFoundException:
        pass

    raise SecretNotFoundError(secret_name)
