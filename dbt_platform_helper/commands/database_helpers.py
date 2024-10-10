import boto3

from dbt_platform_helper.utils.aws import Vpc


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
