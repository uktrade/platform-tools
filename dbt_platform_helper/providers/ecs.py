import random
import string
import time
from typing import List

from dbt_platform_helper.exceptions import ECSAgentNotRunning
from dbt_platform_helper.exceptions import NoClusterError


# TODO Refactor this to support passing a list of tags to check against, allowing for a more generic implementation
def get_cluster_arn(ecs_client, application_name: str, env: str) -> str:
    for cluster_arn in ecs_client.list_clusters()["clusterArns"]:
        tags_response = ecs_client.list_tags_for_resource(resourceArn=cluster_arn)
        tags = tags_response["tags"]

        app_key_found = False
        env_key_found = False
        cluster_key_found = False

        for tag in tags:
            if tag["key"] == "copilot-application" and tag["value"] == application_name:
                app_key_found = True
            if tag["key"] == "copilot-environment" and tag["value"] == env:
                env_key_found = True
            if tag["key"] == "aws:cloudformation:logical-id" and tag["value"] == "Cluster":
                cluster_key_found = True

        if app_key_found and env_key_found and cluster_key_found:
            return cluster_arn

    raise NoClusterError


def get_or_create_task_name(
    ssm_client, application_name: str, env: str, addon_name: str, parameter_name: str
) -> str:
    try:
        return ssm_client.get_parameter(Name=parameter_name)["Parameter"]["Value"]
    except ssm_client.exceptions.ParameterNotFound:
        random_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        return f"conduit-{application_name}-{env}-{addon_name}-{random_id}"


def get_ecs_task_arns(ecs_client, cluster_arn: str, task_name: str):

    tasks = ecs_client.list_tasks(
        cluster=cluster_arn,
        desiredStatus="RUNNING",
        family=f"copilot-{task_name}",
    )

    if not tasks["taskArns"]:
        return []

    return tasks["taskArns"]


def ecs_exec_is_available(ecs_client, cluster_arn: str, task_arns: List[str]):

    current_attemps = 0
    execute_command_agent_status = ""

    while execute_command_agent_status != "RUNNING" and current_attemps < 25:

        current_attemps += 1

        task_details = ecs_client.describe_tasks(cluster=cluster_arn, tasks=task_arns)

        managed_agents = task_details["tasks"][0]["containers"][0]["managedAgents"]
        execute_command_agent_status = [
            agent["lastStatus"]
            for agent in managed_agents
            if agent["name"] == "ExecuteCommandAgent"
        ][0]

        time.sleep(1)

    if execute_command_agent_status != "RUNNING":
        raise ECSAgentNotRunning
