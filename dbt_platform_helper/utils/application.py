import json
import os
import re
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Dict

import boto3

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.aws import get_profile_name_from_account_id
from dbt_platform_helper.utils.aws import get_ssm_secrets
from dbt_platform_helper.utils.messages import abort_with_error


@dataclass
class Environment:
    name: str
    account_id: str
    sessions: Dict[str, boto3.Session]

    @property
    def session(self):
        if self.account_id not in self.sessions:
            self.sessions[self.account_id] = get_aws_session_or_abort(
                get_profile_name_from_account_id(self.account_id),
            )

        return self.sessions[self.account_id]


@dataclass
class Service:
    name: str
    kind: str


@dataclass
class Application:
    name: str
    environments: Dict[str, Environment] = field(default_factory=dict)
    services: Dict[str, Service] = field(default_factory=dict)

    def __str__(self):
        output = f"Application {self.name} with"

        environments = [f"{env.name}:{env.account_id}" for env in self.environments.values()]

        if environments:
            return f"{output} environments {', '.join(environments)}"

        return f"{output} no environments"

    def __eq__(self, other):
        return str(self) == str(other)


def load_application(app=None, default_session=None, env=None) -> Application:
    application = Application(app if app else get_application_name())
    current_session = default_session if default_session else get_aws_session_or_abort()

    ssm_client = current_session.client("ssm")
    sts_client = current_session.client("sts")
    account_id = sts_client.get_caller_identity()["Account"]
    sessions = {account_id: current_session}

    def is_environment_key(name):
        """
        Match only parameter names that are an environment path with no further
        nesting.

        e.g.
         - /copilot/applications/test/environments/my_env will match.
         - /copilot/applications/test/environments/my_env/addons will not match.
        """
        environment_key_regex = r"^/(copilot|platform)/applications/{}/environments/[^/]*$".format(
            application.name
        )
        return bool(re.match(environment_key_regex, name))

    environments_data = []

    # Try to load the new /platform SSM parameter if present
    platform_env_path = f"/platform/applications/{application.name}/environments"
    secrets = get_ssm_secrets(app, None, current_session, platform_env_path)

    if secrets:
        for name, value in secrets:
            try:
                data = json.loads(value)
            except json.JSONDecodeError:
                continue

            # New /platform SSM parameter contains data about all environments
            if "allEnvironments" in data:
                environments_data = data["allEnvironments"]
                break  # Only need one
    else:
        try:
            # Check that the Copilot application exists
            ssm_client.get_parameter(
                Name=f"/copilot/applications/{application.name}",
                WithDecryption=False,
            )
            secrets = get_ssm_secrets(
                app, None, current_session, f"/copilot/applications/{application.name}/environments"
            )

            for name, value in secrets:
                try:
                    data = json.loads(value)
                except json.JSONDecodeError:
                    continue

                if is_environment_key(name):
                    # Legacy /copilot SSM parameter. An individual SSM param is present per environment - looping through all of them is needed to extract necessary data about each env.
                    environments_data.append(data)

        except ssm_client.exceptions.ParameterNotFound:
            raise ApplicationNotFoundException(
                application_name=application.name, environment_name=env
            )

    application.environments = {
        env["name"]: Environment(env["name"], env["accountID"], sessions)
        for env in environments_data
    }

    response = ssm_client.get_parameters_by_path(
        Path=f"/copilot/applications/{application.name}/components",
        Recursive=False,
        WithDecryption=False,
    )
    results = response["Parameters"]
    while "NextToken" in response:
        response = ssm_client.get_parameters_by_path(
            Path=f"/copilot/applications/{application.name}/components",
            Recursive=False,
            WithDecryption=False,
            NextToken=response["NextToken"],
        )
        results.extend(response["Parameters"])

    application.services = {
        svc["name"]: Service(svc["name"], svc["type"])
        for svc in [json.loads(parameter["Value"]) for parameter in results]
    }

    return application


def get_application_name(abort=abort_with_error):
    if Path(PLATFORM_CONFIG_FILE).exists():
        config = ConfigProvider(installed_version_provider="N/A")
        try:
            app_config = config.load_unvalidated_config_file()
            return app_config["application"]
        except KeyError:
            abort(
                f"Cannot get application name. No 'application' key can be found in {PLATFORM_CONFIG_FILE}"
            )
    else:
        abort(f"Cannot get application name. {PLATFORM_CONFIG_FILE} is missing.")


class ApplicationException(PlatformException):
    pass


class ApplicationNotFoundException(ApplicationException):
    def __init__(self, application_name: str, environment_name: str):
        super().__init__(
            f"""The account "{os.environ.get("AWS_PROFILE")}" does not contain the application "{application_name}". 
Please ensure that the environment variable "AWS_PROFILE" is set correctly. If the issue persists, verify that one of the following AWS SSM parameters exists:
 - /platform/applications/{application_name}/environments/{environment_name}
 - /copilot/applications/{application_name}"""
        )


class ApplicationServiceNotFoundException(ApplicationException):
    def __init__(self, application_name: str, svc_name: str):
        super().__init__(
            f"""The service {svc_name} was not found in the application {application_name}. It either does not exist, or has not been deployed."""
        )


class ApplicationEnvironmentNotFoundException(ApplicationException):
    def __init__(self, application_name: str, environment: str):
        super().__init__(
            f"""The environment "{environment}" either does not exist or has not been deployed for the application {application_name}."""
        )
