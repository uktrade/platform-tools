import click

from dbt_platform_helper.commands.database_helpers import DatabaseCopy
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(chain=True, cls=ClickDocOptGroup)
def database():
    pass  # check_platform_helper_version_needs_update()


@database.command(name="dump")
@click.option("--account-id", type=str, required=True)
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
@click.option("--database", type=str, required=True)
@click.option("--vpc-name", type=str, required=True)
def dump(account_id, app, env, database, vpc_name):
    """Dump a database into an S3 bucket."""
    data_copy = DatabaseCopy(account_id, app, env, database, vpc_name)
    data_copy.dump()


@database.command(name="load")
@click.option("--account-id", type=str, required=True)
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
@click.option("--database", type=str, required=True)
@click.option("--vpc-name", type=str, required=True)
def load(account_id, app, env, database, vpc_name):
    """Load a database from an S3 bucket."""
    data_copy = DatabaseCopy(account_id, app, env, database, vpc_name)
    data_copy.load()


# @database.command(name="copy")
# @click.argument("source_db", type=str, required=True)
# @click.argument("target_db", type=str, required=True)
# def copy(source_db: str, target_db: str):
#     """Copy source database to target database."""
#     app = None
#     source_env = None
#     target_env = None
#
#     for tag in get_database_tags(source_db):
#         if tag["Key"] == "copilot-application":
#             app = tag["Value"]
#         if tag["Key"] == "copilot-environment":
#             source_env = tag["Value"]
#             if app is not None:
#                 break
#
#     for tag in get_database_tags(target_db):
#         if tag["Key"] == "copilot-environment":
#             target_env = tag["Value"]
#             break
#
#     if not app or not source_env or not target_env:
#         click.secho(f"""Required database tags not found.""", fg="red")
#         exit(1)
#
#     if target_env == "prod":
#         click.secho(f"""The target database cannot be a production database.""", fg="red")
#         exit(1)
#
#     if source_db == target_db:
#         click.secho(f"""Source and target databases are the same.""", fg="red")
#         exit(1)
#
#     if not click.confirm(
#         click.style("Copying data from ", fg="yellow")
#         + click.style(f"{source_db} ", fg="white", bold=True)
#         + click.style(f"in environment {source_env} to ", fg="yellow", bold=True)
#         + click.style(f"{target_db} ", fg="white", bold=True)
#         + click.style(f"in environment {target_env}\n", fg="yellow", bold=True)
#         + click.style("Do you want to continue?", fg="yellow"),
#     ):
#         exit()
#
#     click.echo(f"""Starting task to copy data from {source_db} to {target_db}""")
#
#     source_db_connection = get_connection_string(app, source_env, source_db)
#     target_db_connection = get_connection_string(app, target_env, target_db)
#
#     application = load_application(app)
#     cluster_arn = get_cluster_arn(application, source_env)
#     task_name = f"database-copy-{app}-{source_env}-{app}-{target_env}"
#
#     if not addon_client_is_running(application, source_env, cluster_arn, task_name):
#         subprocess.call(
#             f"copilot task run --app {app} --env {source_env} "
#             f"--task-group-name {task_name} "
#             f"--image public.ecr.aws/uktrade/tunnel:database-copy "
#             f"--env-vars SOURCE_DB_CONNECTION='{source_db_connection}',TARGET_DB_CONNECTION='{target_db_connection}' "
#             "--platform-os linux "
#             "--platform-arch arm64",
#             shell=True,
#         )
#         add_stack_delete_policy_to_task_role(application, source_env, task_name)
#     connect_to_addon_client_task(application, source_env, cluster_arn, task_name)
#
#
# def get_database_tags(db_identifier: str) -> List[dict]:
#     session = get_aws_session_or_abort()
#     rds = session.client("rds")
#
#     try:
#         db_instance = rds.describe_db_instances(DBInstanceIdentifier=db_identifier)["DBInstances"][
#             0
#         ]
#
#         return db_instance["TagList"]
#     except rds.exceptions.DBInstanceNotFoundFault:
#         click.secho(
#             f"""Database {db_identifier} not found. Check the database identifier.""", fg="red"
#         )
#         exit(1)
#
#
# """
# aws ecs run-task \
#   --task-definition arn:aws:ecs:eu-west-2:891377058512:task-definition/hotfix-demodjango-postgres-restore \
#   --cluster demodjango-hotfix \
#   --capacity-provider-strategy '[{
#         "capacityProvider": "FARGATE",
#             "weight": 1,
#                 "base": 0
#     }]' \
#   --network-configuration '{
#       "awsvpcConfiguration": {
#         "subnets": ["subnet-0ef8bf9b7cc86d6d2"],
#         "securityGroups": ["sg-00055c7e58cba5fde"],
#         "assignPublicIp": "DISABLED"
#       }
#     }' \
#   --overrides '{"containerOverrides": [
#       {
#         "name": "hotfix-demodjango-postgres-restore",
#         "environment": [
#           {
#             "name": "DATA_COPY_OPERATION",
#             "value": "RESTORE"
#           },
#           {
#             "name": "DB_CONNECTION_STRING",
#             "value": "postgres://postgres:banana@demodjango-hotfix-demodjango-postgres.cje2g6iwu5wr.eu-west-2.rds.amazonaws.com:5432/main"
#           }
#         ]
#       }
#     ]}' | tee ${TASK_FILE}
# """

#
# cd ~/paas/platform-tools/images/tools/database-copy2
#
# export AWS_PROFILE=platform-tools
# docker build --tag  public.ecr.aws/uktrade/database-copy:latest .
# docker push public.ecr.aws/uktrade/database-copy:latest
#
# export AWS_PROFILE=platform-prod
# cd ~/paas/demodjango-deploy/terraform/environments/hotfix
#
# TASK_FILE=~/0/task_output.json
# log_group_name="/ecs/data-copy-poc-ant"
#
# aws ecs run-task \
#         --task-definition arn:aws:ecs:eu-west-2:891377058512:task-definition/data-copy-poc-ant \
#                                                              --cluster demodjango-prod \
#                                                                        --capacity-provider-strategy '[{
# "capacityProvider": "FARGATE",
# "weight": 1,
# "base": 0
# }]' \
#   --network-configuration '{
#     "awsvpcConfiguration": {
# "subnets": ["subnet-0539464b3d3c5c4d2"],
# "securityGroups": ["sg-0016f40994bbc1c64"],
# "assignPublicIp": "DISABLED"
# }
# }' \
#   --overrides '{"containerOverrides": [
# {
#     "name": "data-copy",
#     "environment": [
#         {
#             "name": "DATA_COPY_OPERATION",
#             "value": "DUMP"
#         },
#         {
#             "name": "DB_CONNECTION_STRING",
#             "value": "postgres://postgres:banana@demodjango-prod-demodjango-postgres.cje2g6iwu5wr.eu-west-2.rds.amazonaws.com:5432/main"
#         }
#     ]
# }
# ]}' | tee ${TASK_FILE}
#
# task_arn=$(cat ${TASK_FILE} | jq -r '.tasks[0].taskArn')
# cluster_arn=$(cat ${TASK_FILE} | jq -r '.tasks[0].clusterArn')
#
#
# timestamp=$(date +"%Y-%m-%dT%H:%M:%S%z")
#
# echo "Data Dump Logs:"
# aws ecs wait tasks-stopped --cluster "${cluster_arn}" --tasks "${task_arn}"
#
# aws logs tail ${log_group_name} --since ${timestamp} --output text
#
# # last_status=
# # while [ "${last_status}" != "DEPROVISIONING" ] && [ "${last_status}" != "STOPPED" ]
# # do
# # sleep 5
# # TASK_DESC=$(aws ecs describe-tasks --cluster "${cluster_arn}" --tasks "${task_arn}" | tee some_file.txt)
# # last_status=$(echo ${TASK_DESC} | jq -r '.tasks[0].lastStatus')
# # echo STATUS: ${last_status}
# #
# # if [ "${last_status}" == "RUNNING" ]
# # then
# # cat some_file.txt
# # fi
# # done
#
#
# aws ecs run-task \
#         --task-definition arn:aws:ecs:eu-west-2:891377058512:task-definition/data-copy-poc-ant \
#                                                              --cluster demodjango-hotfix \
#                                                                        --capacity-provider-strategy '[{
#                                                                                                     "capacityProvider": "FARGATE",
# "weight": 1,
# "base": 0
# }]' \
#   --network-configuration '{
#     "awsvpcConfiguration": {
#         "subnets": ["subnet-0ef8bf9b7cc86d6d2"],
#         "securityGroups": ["sg-00055c7e58cba5fde"],
#         "assignPublicIp": "DISABLED"
#     }
# }' \
#   --overrides '{"containerOverrides": [
#     {
#         "name": "data-copy",
#         "environment": [
# {
#     "name": "DATA_COPY_OPERATION",
#     "value": "RESTORE"
# },
# {
#     "name": "DB_CONNECTION_STRING",
#     "value": "postgres://postgres:banana@demodjango-hotfix-demodjango-postgres.cje2g6iwu5wr.eu-west-2.rds.amazonaws.com:5432/main"
# }
# ]
# }
# ]}' | tee ${TASK_FILE}
#
# task_arn=$(cat ${TASK_FILE} | jq -r '.tasks[0].taskArn')
# cluster_arn=$(cat ${TASK_FILE} | jq -r '.tasks[0].clusterArn')
#
#
# timestamp=$(date +"%Y-%m-%dT%H:%M:%S%z")
#
# echo "Data Restore Logs:"
# aws ecs wait tasks-stopped --cluster "${cluster_arn}" --tasks "${task_arn}"
#
# aws logs tail ${log_group_name} --since ${timestamp} --output text
# # "value": "postgres://postgres:%(Alse%k]m~yLzZl:Q6iT0punfvk@demodjango-hotfix-demodjango-postgres.cje2g6iwu5wr.eu-west-2.rds.amazonaws.com:5432/main"
#
# aws s3 rm s3://data-copy-poc-ant/data_dump.tgz
#
# echo DONE
#
