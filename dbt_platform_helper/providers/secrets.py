import json
import urllib

from dbt_platform_helper.constants import CONDUIT_ADDON_TYPES
from dbt_platform_helper.platform_exception import PlatformException


class Secrets:
    def __init__(self, ssm_client, secrets_manager_client, application_name, env):
        self.ssm_client = ssm_client
        self.secrets_manager_client = secrets_manager_client
        self.application_name = application_name
        self.env = env

    def get_postgres_connection_data_updated_with_master_secret(self, parameter_name, secret_arn):
        response = self.ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
        parameter_value = response["Parameter"]["Value"]

        parameter_data = json.loads(parameter_value)

        secret_response = self.secrets_manager_client.get_secret_value(SecretId=secret_arn)
        secret_value = json.loads(secret_response["SecretString"])

        parameter_data["username"] = urllib.parse.quote(secret_value["username"])
        parameter_data["password"] = urllib.parse.quote(secret_value["password"])

        return parameter_data

    def get_connection_secret_arn(self, secret_name: str) -> str:
        try:
            return self.ssm_client.get_parameter(Name=secret_name, WithDecryption=False)[
                "Parameter"
            ]["ARN"]
        except self.ssm_client.exceptions.ParameterNotFound:
            pass

        try:
            return self.secrets_manager_client.describe_secret(SecretId=secret_name)["ARN"]
        except self.secrets_manager_client.exceptions.ResourceNotFoundException:
            pass

        raise SecretNotFoundException(secret_name)

    # TODO: DBTP-1946: This probably does not belong in the secrets provider. When it moves, take the Todoed exceptions from below
    def get_addon_type(self, addon_name: str) -> str:
        addon_type = None
        try:
            addon_config = json.loads(
                self.ssm_client.get_parameter(
                    Name=f"/copilot/applications/{self.application_name}/environments/{self.env}/addons"
                )["Parameter"]["Value"]
            )
        except self.ssm_client.exceptions.ParameterNotFound:
            raise ParameterNotFoundException(self.application_name, self.env)

        if addon_name not in addon_config.keys():
            raise AddonNotFoundException(addon_name)

        for name, config in addon_config.items():
            if name == addon_name:
                if not config.get("type"):
                    raise AddonTypeMissingFromConfigException(addon_name)
                addon_type = config["type"]

        if not addon_type or addon_type not in CONDUIT_ADDON_TYPES:
            raise InvalidAddonTypeException(addon_type)

        if "postgres" in addon_type:
            addon_type = "postgres"

        return addon_type

    def get_parameter_name(self, addon_type: str, addon_name: str, access: str) -> str:
        if addon_type == "postgres":
            return f"/copilot/{self.application_name}/{self.env}/conduits/{self._normalise_secret_name(addon_name)}_{access.upper()}"
        elif addon_type == "redis" or addon_type == "opensearch":
            return f"/copilot/{self.application_name}/{self.env}/conduits/{self._normalise_secret_name(addon_name)}_ENDPOINT"
        else:
            return f"/copilot/{self.application_name}/{self.env}/conduits/{self._normalise_secret_name(addon_name)}"

    def _normalise_secret_name(self, addon_name: str) -> str:
        return addon_name.replace("-", "_").upper()


# TODO: DBTP-1946: This probably does not belong in the secrets provider. Move it when we find a better home for get_addon_type()
class AddonException(PlatformException):
    pass


# TODO: DBTP-1946: This probably does not belong in the secrets provider. Move it when we find a better home for get_addon_type()
class AddonNotFoundException(AddonException):
    def __init__(self, addon_name: str):
        super().__init__(f"""Addon "{addon_name}" does not exist.""")


# TODO: DBTP-1946: This probably does not belong in the secrets provider. Move it when we find a better home for get_addon_type()
class AddonTypeMissingFromConfigException(AddonException):
    def __init__(self, addon_name: str):
        super().__init__(
            f"""The configuration for the addon {addon_name}, is misconfigured and missing the addon type."""
        )


# TODO: DBTP-1946: This probably does not belong in the secrets provider. Move it when we find a better home for get_addon_type()
class InvalidAddonTypeException(AddonException):
    def __init__(self, addon_type):
        self.addon_type = addon_type
        super().__init__(
            f"""Addon type "{self.addon_type}" is not supported, we support: {", ".join(CONDUIT_ADDON_TYPES)}."""
        )


class SecretException(PlatformException):
    pass


class ParameterNotFoundException(SecretException):
    def __init__(self, application_name: str, environment: str):
        super().__init__(
            f"""No parameter called "/copilot/applications/{application_name}/environments/{environment}/addons". Try deploying the "{application_name}" "{environment}" environment."""
        )


class SecretNotFoundException(SecretException):
    def __init__(self, secret_name: str):
        super().__init__(f"""No secret called "{secret_name}".""")
