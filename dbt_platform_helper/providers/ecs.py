import random
import string
import time
from typing import List

from dbt_platform_helper.platform_exception import PlatformException


class ECS:
    def __init__(self, ecs_client, ssm_client, application_name: str, env: str):
        self.ecs_client = ecs_client
        self.ssm_client = ssm_client
        self.application_name = application_name
        self.env = env

    def get_cluster_arn(self) -> str:
        """Returns the ARN of the ECS cluster for the given application and
        environment."""
        for cluster_arn in self.ecs_client.list_clusters()["clusterArns"]:
            tags_response = self.ecs_client.list_tags_for_resource(resourceArn=cluster_arn)
            tags = tags_response["tags"]

            app_key_found = False
            env_key_found = False
            cluster_key_found = False

            for tag in tags:
                if tag["key"] == "copilot-application" and tag["value"] == self.application_name:
                    app_key_found = True
                if tag["key"] == "copilot-environment" and tag["value"] == self.env:
                    env_key_found = True
                if tag["key"] == "aws:cloudformation:logical-id" and tag["value"] == "Cluster":
                    cluster_key_found = True

            if app_key_found and env_key_found and cluster_key_found:
                return cluster_arn

        raise NoClusterException(self.application_name, self.env)

    def get_or_create_task_name(self, addon_name: str, parameter_name: str) -> str:
        """Fetches the task name from SSM or creates a new one if not found."""
        try:
            return self.ssm_client.get_parameter(Name=parameter_name)["Parameter"]["Value"]
        except self.ssm_client.exceptions.ParameterNotFound:
            random_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
            return f"conduit-{self.application_name}-{self.env}-{addon_name}-{random_id}"

    def get_ecs_task_arns(self, cluster_arn: str, task_name: str):
        """Gets the ECS task ARNs for a given task name and cluster ARN."""
        tasks = self.ecs_client.list_tasks(
            cluster=cluster_arn,
            desiredStatus="RUNNING",
            family=f"copilot-{task_name}",
        )

        if not tasks["taskArns"]:
            return []

        return tasks["taskArns"]

    def ecs_exec_is_available(self, cluster_arn: str, task_arns: List[str]):
        """
        Checks if the ExecuteCommandAgent is running on the specified ECS task.

        Waits for up to 25 attempts, then raises ECSAgentNotRunning if still not
        running.
        """
        current_attempts = 0
        execute_command_agent_status = ""

        while execute_command_agent_status != "RUNNING" and current_attempts < 25:
            current_attempts += 1

            task_details = self.ecs_client.describe_tasks(cluster=cluster_arn, tasks=task_arns)

            managed_agents = task_details["tasks"][0]["containers"][0]["managedAgents"]
            execute_command_agent_status = [
                agent["lastStatus"]
                for agent in managed_agents
                if agent["name"] == "ExecuteCommandAgent"
            ][0]
            if execute_command_agent_status != "RUNNING":
                time.sleep(1)

        if execute_command_agent_status != "RUNNING":
            raise ECSAgentNotRunningException


class ECSException(PlatformException):
    pass


class ECSAgentNotRunningException(ECSException):
    def __init__(self):
        super().__init__("""ECS exec agent never reached "RUNNING" status""")


class NoClusterException(ECSException):
    def __init__(self, application_name: str, environment: str):
        super().__init__(
            f"""No ECS cluster found for "{application_name}" in "{environment}" environment."""
        )
