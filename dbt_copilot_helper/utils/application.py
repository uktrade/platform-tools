import json
from pathlib import Path
from typing import Dict

import boto3
import yaml
from boto3 import Session
from yaml.parser import ParserError

from dbt_copilot_helper.utils.aws import get_aws_session_or_abort
from dbt_copilot_helper.utils.aws import get_profile_name_from_account_id
from dbt_copilot_helper.utils.files import load_and_validate_config
from dbt_copilot_helper.utils.messages import abort_with_error
from dbt_copilot_helper.utils.validation import BOOTSTRAP_SCHEMA


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


class Application:
    name: str
    environments: Dict[str, Environment]

    def __init__(self, name: str):
        self.name = name
        self.environments = {}

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

    response = ssm_client.get_parameters_by_path(
        Path=f"/copilot/applications/{application.name}/environments",
        Recursive=True,
        WithDecryption=False,
    )

    sts_client = current_session.client("sts")
    account_id = sts_client.get_caller_identity()["Account"]
    sessions = {account_id: current_session}

    application.environments = {
        env["name"]: Environment(env["name"], env["accountID"], sessions)
        for env in [json.loads(p["Value"]) for p in response["Parameters"]]
    }

    return application


def get_application_name():
    app_name = None

    try:
        app_config = load_and_validate_config("bootstrap.yml", BOOTSTRAP_SCHEMA)
        app_name = app_config["app"]
    except (FileNotFoundError, ParserError):
        pass

    try:
        if app_name is None:
            app_config = yaml.safe_load(Path("copilot/.workspace").read_text())
            app_name = app_config["application"]
    except (FileNotFoundError, ParserError):
        pass

    if app_name is None:
        abort_with_error("No valid bootstrap.yml or copilot/.workspace file found")

    return app_name
