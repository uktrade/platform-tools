import json
import urllib


# TODO exceptions
class AWSError(Exception):
    pass


class SecretNotFoundError(AWSError):
    pass


# TODO extract some business knowledge
def get_postgres_connection_data_updated_with_master_secret(
    ssm_client, secrets_manager_client, parameter_name, secret_arn
):
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
