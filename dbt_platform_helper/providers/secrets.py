import json
import urllib

from dbt_platform_helper.constants import CONDUIT_ADDON_TYPES
from dbt_platform_helper.exceptions import AddonNotFoundError
from dbt_platform_helper.exceptions import AddonTypeMissingFromConfigError
from dbt_platform_helper.exceptions import InvalidAddonTypeError
from dbt_platform_helper.exceptions import ParameterNotFoundError
from dbt_platform_helper.exceptions import SecretNotFoundError


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


def get_addon_type(ssm_client, application_name: str, env: str, addon_name: str) -> str:
    addon_type = None
    try:
        addon_config = json.loads(
            ssm_client.get_parameter(
                Name=f"/copilot/applications/{application_name}/environments/{env}/addons"
            )["Parameter"]["Value"]
        )
    except ssm_client.exceptions.ParameterNotFound:
        raise ParameterNotFoundError

    if addon_name not in addon_config.keys():
        raise AddonNotFoundError

    for name, config in addon_config.items():
        if name == addon_name:
            if not config.get("type"):
                raise AddonTypeMissingFromConfigError()
            addon_type = config["type"]

    if not addon_type or addon_type not in CONDUIT_ADDON_TYPES:
        raise InvalidAddonTypeError(addon_type)

    if "postgres" in addon_type:
        addon_type = "postgres"

    return addon_type


def get_parameter_name(
    application_name: str, env: str, addon_type: str, addon_name: str, access: str
) -> str:
    if addon_type == "postgres":
        return f"/copilot/{application_name}/{env}/conduits/{_normalise_secret_name(addon_name)}_{access.upper()}"
    elif addon_type == "redis" or addon_type == "opensearch":
        return f"/copilot/{application_name}/{env}/conduits/{_normalise_secret_name(addon_name)}_ENDPOINT"
    else:
        return f"/copilot/{application_name}/{env}/conduits/{_normalise_secret_name(addon_name)}"


def _normalise_secret_name(addon_name: str) -> str:
    return addon_name.replace("-", "_").upper()
