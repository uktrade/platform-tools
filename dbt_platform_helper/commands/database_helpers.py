from collections.abc import Callable
from pathlib import Path

import boto3
import click
from boto3 import Session

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.exceptions import AWSException
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import ApplicationNotFoundError
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.aws import Vpc
from dbt_platform_helper.utils.aws import get_connection_string
from dbt_platform_helper.utils.aws import get_vpc_info_by_name
from dbt_platform_helper.utils.messages import abort_with_error
from dbt_platform_helper.utils.validation import load_and_validate_platform_config


class DatabaseCopy:
    def __init__(
        self,
        app: str | None,
        database: str,
        load_application_fn: Callable[[str], Application] = load_application,
        vpc_config_fn: Callable[[Session, str, str, str], Vpc] = get_vpc_info_by_name,
        db_connection_string_fn: Callable[
            [Session, str, str, str, Callable], str
        ] = get_connection_string,
        input_fn: Callable[[str], str] = click.prompt,
        echo_fn: Callable[[str], str] = click.secho,
        abort_fn: Callable[[str], None] = abort_with_error,
    ):
        self.app = app
        self.database = database
        self.vpc_config_fn = vpc_config_fn
        self.db_connection_string_fn = db_connection_string_fn
        self.input_fn = input_fn
        self.echo_fn = echo_fn
        self.abort_fn = abort_fn

        if not self.app:
            if not Path(PLATFORM_CONFIG_FILE).exists():
                self.abort_fn("You must either be in a deploy repo, or provide the --app option.")

            config = load_and_validate_platform_config(disable_aws_validation=True)
            self.app = config["application"]

        try:
            self.application = load_application_fn(self.app)
        except ApplicationNotFoundError:
            abort_fn(f"No such application '{app}'.")

    def _execute_operation(self, is_dump: bool, env: str, vpc_name: str):
        environments = self.application.environments
        environment = environments.get(env)
        if not environment:
            self.abort_fn(
                f"No such environment '{env}'. Available environments are: {', '.join(environments.keys())}"
            )

        env_session = environment.session

        try:
            vpc_config = self.vpc_config_fn(env_session, self.app, env, vpc_name)
        except AWSException as ex:
            self.abort_fn(str(ex))

        database_identifier = f"{self.app}-{env}-{self.database}"

        try:
            db_connection_string = self.db_connection_string_fn(
                env_session, self.app, env, database_identifier
            )
        except Exception as exc:
            self.abort_fn(f"{exc} (Database: {database_identifier})")

        try:
            task_arn = self.run_database_copy_task(
                env_session, env, vpc_config, is_dump, db_connection_string
            )
        except Exception as exc:
            self.abort_fn(f"{exc} (Account id: {self.account_id(env)})")

        if is_dump:
            message = f"Dumping {self.database} from the {env} environment into S3"
        else:
            message = f"Loading data into {self.database} in the {env} environment from S3"

        self.echo_fn(message, fg="white", bold=True)
        self.echo_fn(
            f"Task {task_arn} started. Waiting for it to complete (this may take some time)...",
            fg="white",
        )
        self.tail_logs(is_dump, env)

    def run_database_copy_task(
        self,
        session: boto3.session.Session,
        env: str,
        vpc_config: Vpc,
        is_dump: bool,
        db_connection_string: str,
    ) -> str:
        client = session.client("ecs")
        action = "dump" if is_dump else "load"
        response = client.run_task(
            taskDefinition=f"arn:aws:ecs:eu-west-2:{self.account_id(env)}:task-definition/{self.app}-{env}-{self.database}-{action}",
            cluster=f"{self.app}-{env}",
            capacityProviderStrategy=[
                {"capacityProvider": "FARGATE", "weight": 1, "base": 0},
            ],
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": vpc_config.subnets,
                    "securityGroups": vpc_config.security_groups,
                    "assignPublicIp": "DISABLED",
                }
            },
            overrides={
                "containerOverrides": [
                    {
                        "name": f"{self.app}-{env}-{self.database}-{action}",
                        "environment": [
                            {"name": "DATA_COPY_OPERATION", "value": action.upper()},
                            {"name": "DB_CONNECTION_STRING", "value": db_connection_string},
                        ],
                    }
                ]
            },
        )

        return response.get("tasks", [{}])[0].get("taskArn")

    def dump(self, env: str, vpc_name: str):
        self._execute_operation(True, env, vpc_name)

    def load(self, env: str, vpc_name: str):
        if self.is_confirmed_ready_to_load(env):
            self._execute_operation(False, env, vpc_name)

    def is_confirmed_ready_to_load(self, env: str) -> bool:
        user_input = self.input_fn(
            f"\nAre all tasks using {self.database} in the {env} environment stopped? (y/n)"
        )
        return user_input.lower().strip() in ["y", "yes"]

    def tail_logs(self, is_dump: bool, env: str):
        action = "dump" if is_dump else "load"
        log_group_name = f"/ecs/{self.app}-{env}-{self.database}-{action}"
        log_group_arn = f"arn:aws:logs:eu-west-2:{self.account_id(env)}:log-group:{log_group_name}"
        self.echo_fn(f"Tailing logs for {log_group_name}", fg="yellow")
        session = self.application.environments[env].session
        response = session.client("logs").start_live_tail(logGroupIdentifiers=[log_group_arn])

        stopped = False
        for data in response["responseStream"]:
            if stopped:
                break
            results = data.get("sessionUpdate", {}).get("sessionResults", [])
            for result in results:
                message = result.get("message")

                if message:
                    if message.startswith("Stopping data "):
                        stopped = True
                    self.echo_fn(message)

    def account_id(self, env):
        envs = self.application.environments
        if env in envs:
            return envs.get(env).account_id
