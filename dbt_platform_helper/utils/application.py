import json
import re
from pathlib import Path
from typing import Dict

import boto3
import yaml
from boto3 import Session
from yaml.parser import ParserError

from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.aws import get_profile_name_from_account_id
from dbt_platform_helper.utils.aws import get_ssm_secrets
from dbt_platform_helper.utils.messages import abort_with_error


class Environment:
    name: str
    account_id: str
    sessions: Dict[str, boto3.Session]

    def __init__(self, name: str, account_id: str, sessions: Dict[str, boto3.Session]):
        self.name = name
        self.account_id = account_id
        self.sessions = sessions

    @property
    def session(self):
        if self.account_id not in self.sessions:
            self.sessions[self.account_id] = get_aws_session_or_abort(
                get_profile_name_from_account_id(self.account_id),
            )

        return self.sessions[self.account_id]


class Service:
    name: str
    kind: str

    def __init__(self, name: str, kind: str):
        self.name = name
        self.kind = kind


class Application:
    name: str
    environments: Dict[str, Environment]
    services: Dict[str, Service]

    def __init__(self, name: str):
        self.name = name
        self.environments = {}
        self.services = {}

    def __str__(self):
        output = f"Application {self.name} with"

        environments = [f"{env.name}:{env.account_id}" for env in self.environments.values()]

        if environments:
            return f"{output} environments {', '.join(environments)}"

        return f"{output} no environments"

    def __eq__(self, other):
        return str(self) == str(other)


class ApplicationNotFoundError(Exception):
    pass


def load_application(app: str = None, default_session: Session = None) -> Application:
    application = Application(app if app else get_application_name())
    current_session = default_session if default_session else get_aws_session_or_abort()

    ssm_client = current_session.client("ssm")

    try:
        ssm_client.get_parameter(
            Name=f"/copilot/applications/{application.name}",
            WithDecryption=False,
        )
    except ssm_client.exceptions.ParameterNotFound:
        raise ApplicationNotFoundError

    path = f"/copilot/applications/{application.name}/environments"
    secrets = get_ssm_secrets(app, None, current_session, path)

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
        environment_key_regex = r"^/copilot/applications/{}/environments/[^/]*$".format(
            application.name
        )
        return bool(re.match(environment_key_regex, name))

    environments = {
        env["name"]: Environment(env["name"], env["accountID"], sessions)
        for env in [json.loads(s[1]) for s in secrets if is_environment_key(s[0])]
    }
    application.environments = environments

    response = ssm_client.get_parameters_by_path(
        Path=f"/copilot/applications/{application.name}/components",
        Recursive=False,
        WithDecryption=False,
    )

    application.services = {
        svc["name"]: Service(svc["name"], svc["type"])
        for svc in [json.loads(parameter["Value"]) for parameter in response["Parameters"]]
    }

    return application


def get_application_name():
    app_name = None
    try:
        app_config = yaml.safe_load(Path("copilot/.workspace").read_text())
        app_name = app_config["application"]
    except (FileNotFoundError, ParserError):
        pass

    if app_name is None:
        abort_with_error("Cannot get application name. No copilot/.workspace file found")

    return app_name
