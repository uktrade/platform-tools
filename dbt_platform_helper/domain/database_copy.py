import re
from collections.abc import Callable
from pathlib import Path

import boto3
from boto3 import Session

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.domain.maintenance_page import MaintenancePage
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.io import ClickIOProviderException
from dbt_platform_helper.providers.vpc import Vpc
from dbt_platform_helper.providers.vpc import VpcProvider
from dbt_platform_helper.providers.vpc import VpcProviderException
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import ApplicationNotFoundException
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.aws import get_connection_string
from dbt_platform_helper.utils.aws import wait_for_log_group_to_exist


class DatabaseCopy:
    def __init__(
        self,
        app: str,
        database: str,
        auto_approve: bool = False,
        load_application: Callable[[str], Application] = load_application,
        # TODO: DBTP-1960: We inject VpcProvider as a callable here so that it can be instantiated within the method.  To be improved
        vpc_provider: Callable[[Session], VpcProvider] = VpcProvider,
        db_connection_string: Callable[
            [Session, str, str, str, Callable], str
        ] = get_connection_string,
        maintenance_page: Callable[[str, str, list[str], str, str], None] = MaintenancePage,
        io: ClickIOProvider = ClickIOProvider(),
        config_provider: ConfigProvider = ConfigProvider(ConfigValidator()),
    ):
        self.app = app
        self.database = database
        self.auto_approve = auto_approve
        self.vpc_provider = vpc_provider
        self.db_connection_string = db_connection_string
        self.io = io
        self.config_provider = config_provider

        if not self.app:
            if not Path(PLATFORM_CONFIG_FILE).exists():
                self.io.abort_with_error(
                    "You must either be in a deploy repo, or provide the --app option."
                )

            config = self.config_provider.load_and_validate_platform_config()
            self.app = config["application"]

        try:
            self.application = load_application(self.app)
        except ApplicationNotFoundException:
            self.io.abort_with_error(f"No such application '{app}'.")

        self.maintenance_page = maintenance_page(self.application)

    def _execute_operation(self, is_dump: bool, env: str, vpc_name: str, filename: str):
        vpc_name = self.enrich_vpc_name(env, vpc_name)

        environments = self.application.environments
        environment = environments.get(env)
        if not environment:
            self.io.abort_with_error(
                f"No such environment '{env}'. Available environments are: {', '.join(environments.keys())}"
            )

        env_session = environment.session

        try:
            vpc_provider = self.vpc_provider(env_session)
            vpc_config = vpc_provider.get_vpc(self.app, env, vpc_name)
        except VpcProviderException as ex:
            self.io.abort_with_error(str(ex))

        if not vpc_config.security_groups:
            self.io.abort_with_error(f"No security groups found in vpc '{vpc_name}'")

        database_identifier = f"{self.app}-{env}-{self.database}"

        try:
            db_connection_string = self.db_connection_string(
                env_session, self.app, env, database_identifier
            )
        except Exception as exc:
            self.io.abort_with_error(f"{exc} (Database: {database_identifier})")

        try:
            task_arn = self.run_database_copy_task(
                env_session, env, vpc_config, is_dump, db_connection_string, filename
            )
        except Exception as exc:
            self.io.abort_with_error(f"{exc} (Account id: {self.account_id(env)})")

        if is_dump:
            message = f"Dumping {self.database} from the {env} environment into S3"
        else:
            message = f"Loading data into {self.database} in the {env} environment from S3"

        self.io.info(message)
        self.io.info(
            f"Task {task_arn} started. Waiting for it to complete (this may take some time)..."
        )
        self.tail_logs(is_dump, env)

    def enrich_vpc_name(self, env, vpc_name):
        if not vpc_name:
            if not Path(PLATFORM_CONFIG_FILE).exists():
                self.io.abort_with_error(
                    "You must either be in a deploy repo, or provide the vpc name option."
                )
            config = self.config_provider.load_and_validate_platform_config()
            env_config = self.config_provider.apply_environment_defaults(config)["environments"]
            vpc_name = env_config.get(env, {}).get("vpc")
        return vpc_name

    def run_database_copy_task(
        self,
        session: boto3.session.Session,
        env: str,
        vpc: Vpc,
        is_dump: bool,
        db_connection_string: str,
        filename: str,
    ) -> str:
        client = session.client("ecs")
        action = "dump" if is_dump else "load"
        dump_file_name = filename if filename else "data_dump"
        env_vars = [
            {"name": "DATA_COPY_OPERATION", "value": action.upper()},
            {"name": "DB_CONNECTION_STRING", "value": db_connection_string},
            {"name": "DUMP_FILE_NAME", "value": dump_file_name},
        ]
        if not is_dump:
            env_vars.append({"name": "ECS_CLUSTER", "value": f"{self.app}-{env}"})

        response = client.run_task(
            taskDefinition=f"arn:aws:ecs:eu-west-2:{self.account_id(env)}:task-definition/{self.app}-{env}-{self.database}-{action}",
            cluster=f"{self.app}-{env}",
            capacityProviderStrategy=[
                {"capacityProvider": "FARGATE", "weight": 1, "base": 0},
            ],
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": vpc.private_subnets,
                    "securityGroups": vpc.security_groups,
                    "assignPublicIp": "DISABLED",
                }
            },
            overrides={
                "containerOverrides": [
                    {
                        "name": f"{self.app}-{env}-{self.database}-{action}",
                        "environment": env_vars,
                    }
                ]
            },
        )

        return response.get("tasks", [{}])[0].get("taskArn")

    def dump(self, env: str, vpc_name: str, filename: str = None):
        self._execute_operation(True, env, vpc_name, filename)

    def load(self, env: str, vpc_name: str, filename: str = None):
        if self.is_confirmed_ready_to_load(env):
            self._execute_operation(False, env, vpc_name, filename)

    def copy(
        self,
        from_env: str,
        to_env: str,
        from_vpc: str,
        to_vpc: str,
        services: tuple[str],
        template: str,
        no_maintenance_page: bool = False,
    ):
        to_vpc = self.enrich_vpc_name(to_env, to_vpc)
        if not no_maintenance_page:
            self.maintenance_page.activate(to_env, services, template, to_vpc)
        self.dump(from_env, from_vpc, f"data_dump_{to_env}")
        self.load(to_env, to_vpc, f"data_dump_{to_env}")
        if not no_maintenance_page:
            self.maintenance_page.deactivate(to_env)

    def is_confirmed_ready_to_load(self, env: str) -> bool:
        if self.auto_approve:
            return True
        try:
            return self.io.confirm(
                f"\nWARNING: the load operation is destructive and will delete the {self.database} database in the {env} environment. Continue?"
            )
        except ClickIOProviderException:
            return False

    def tail_logs(self, is_dump: bool, env: str):
        action = "dump" if is_dump else "load"
        log_group_name = f"/ecs/{self.app}-{env}-{self.database}-{action}"
        log_group_arn = f"arn:aws:logs:eu-west-2:{self.account_id(env)}:log-group:{log_group_name}"
        self.io.warn(f"Tailing {log_group_name} logs")
        session = self.application.environments[env].session
        log_client = session.client("logs")
        wait_for_log_group_to_exist(log_client, log_group_name)
        response = log_client.start_live_tail(logGroupIdentifiers=[log_group_arn])

        stopped = False
        for data in response["responseStream"]:
            if stopped:
                break
            results = data.get("sessionUpdate", {}).get("sessionResults", [])
            for result in results:
                message = result.get("message")

                if message:
                    match = re.match(r"(Stopping|Aborting) data (load|dump).*", message)
                    if match:
                        if match.group(1) == "Aborting":
                            self.io.abort_with_error(
                                "Task aborted abnormally. See logs above for details."
                            )
                        stopped = True
                    self.io.info(message)

    def account_id(self, env):
        envs = self.application.environments
        if env in envs:
            return envs.get(env).account_id
