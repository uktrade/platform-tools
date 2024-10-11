import boto3

from dbt_platform_helper.utils.aws import Vpc
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.aws import get_connection_string
from dbt_platform_helper.utils.aws import get_vpc_info_by_name


def run_database_copy_task(
    session: boto3.session.Session,
    account_id: str,
    app: str,
    env: str,
    database: str,
    vpc_config: Vpc,
    is_dump: bool,
    db_connection_string: str,
):
    client = session.client("ecs")
    action = "dump" if is_dump else "load"
    client.run_task(
        taskDefinition=f"arn:aws:ecs:eu-west-2:{account_id}:task-definition/{env}-{database}-{action}",
        cluster=f"{app}-{env}",
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
                    "name": f"{env}-{database}-{action}",
                    "environment": [
                        {"name": "DATA_COPY_OPERATION", "value": action.upper()},
                        {"name": "DB_CONNECTION_STRING", "value": db_connection_string},
                    ],
                }
            ]
        },
    )


class DatabaseCopy:
    def __init__(
        self,
        account_id,
        app,
        env,
        database,
        vpc_name,
        get_session_fn=get_aws_session_or_abort,
        run_database_copy_fn=run_database_copy_task,
        vpc_config_fn=get_vpc_info_by_name,
        db_connection_string_fn=get_connection_string,
        input_fn=input,
    ):
        self.account_id = account_id
        self.app = app
        self.env = env
        self.database = database
        self.vpc_name = vpc_name
        self.get_session_fn = get_session_fn
        self.run_database_copy_fn = run_database_copy_fn
        self.vpc_config_fn = vpc_config_fn
        self.db_connection_string_fn = db_connection_string_fn
        self.input_fn = input_fn

    def _execute_operation(self, is_dump):
        session = self.get_session_fn()
        vpc_config = self.vpc_config_fn(session, self.app, self.env, self.vpc_name)
        database_identifier = f"{self.app}-{self.env}-{self.database}"
        db_connection_string = self.db_connection_string_fn(
            session, self.app, self.env, database_identifier
        )
        self.run_database_copy_fn(
            session,
            self.account_id,
            self.app,
            self.env,
            self.database,
            vpc_config,
            is_dump,
            db_connection_string,
        )

    def dump(self):
        self._execute_operation(True)

    def load(self):
        if self.is_confirmed_ready_to_load(self.env, self.database):
            self._execute_operation(False)

    def is_confirmed_ready_to_load(self, env, database):
        user_input = self.input_fn(
            f"Are all tasks using {database} in the {env} environment stopped? (y/n)"
        )
        return user_input.lower().strip() in ["y", "yes"]
