import random
import string
import subprocess
from typing import Any
from typing import Optional

from botocore.exceptions import ClientError

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.platform_exception import ValidationException
from dbt_platform_helper.providers.vpc import Vpc
from dbt_platform_helper.utilities.decorators import retry
from dbt_platform_helper.utilities.decorators import wait_until


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


class ECS:
    def __init__(self, ecs_client, ssm_client, application_name: str, env: str):
        self.ecs_client = ecs_client
        self.ssm_client = ssm_client
        self.application_name = application_name
        self.env = env

    def start_ecs_task(
        self,
        cluster_name: str,
        container_name: str,
        task_def_arn: str,
        vpc_config: Vpc,
        env_vars: list[dict] = None,
    ):
        container_override = {"name": container_name}
        if env_vars:
            container_override["environment"] = env_vars

        response = self.ecs_client.run_task(
            taskDefinition=task_def_arn,
            cluster=cluster_name,
            capacityProviderStrategy=[
                {"capacityProvider": "FARGATE", "weight": 1, "base": 0},
            ],
            enableExecuteCommand=True,
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": vpc_config.public_subnets,
                    "securityGroups": vpc_config.security_groups,
                    "assignPublicIp": "ENABLED",
                }
            },
            overrides={"containerOverrides": [container_override]},
        )

        return response.get("tasks", [{}])[0].get("taskArn")

    def get_cluster_arn_by_name(self, cluster_name: str) -> str:
        clusters = self.ecs_client.describe_clusters(
            clusters=[
                cluster_name,
            ],
        )["clusters"]
        if len(clusters) == 1 and "clusterArn" in clusters[0]:
            return clusters[0]["clusterArn"]

        raise NoClusterException(self.application_name, self.env)

    def get_cluster_arn_by_copilot_tag(self) -> str:
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

    def get_ecs_task_arns(
        self,
        cluster: str,
        max_results: int = 100,
        desired_status: str = "RUNNING",
        service_name: Optional[str] = None,
        started_by: Optional[str] = None,
        task_def_family: Optional[str] = None,
    ) -> list[str]:
        """Returns the ECS task ARNs based on the parameters provided."""

        params = {
            "cluster": cluster,
            "maxResults": max_results,
            "desiredStatus": desired_status,
        }

        if service_name:
            params["serviceName"] = service_name
        if started_by:
            params["startedBy"] = started_by
        if task_def_family:
            params["family"] = task_def_family

        tasks = self.ecs_client.list_tasks(**params)

        if not tasks["taskArns"]:
            return []

        return tasks["taskArns"]

    @retry()
    def exec_task(self, cluster_arn: str, task_arn: str, subprocess_call=subprocess.call):
        result = subprocess_call(
            f"aws ecs execute-command --cluster {cluster_arn} "
            f"--task {task_arn} "
            f"--interactive --command bash ",
            shell=True,
        )
        if result != 0:
            raise PlatformException("Failed to exec into ECS task.")
        return result

    @wait_until(
        max_attempts=25,
        exceptions_to_catch=(ECSException,),
        message_on_false="ECS Agent Not running",
    )
    def ecs_exec_is_available(self, cluster_arn: str, task_arns: list[str]) -> bool:
        """
        Checks if the ExecuteCommandAgent is running on the specified ECS task.

        Waits for up to 25 attempts, then raises ECSAgentNotRunning if still not
        running.
        """
        if not task_arns:
            raise ValidationException("No task ARNs provided")
        task_details = self.ecs_client.describe_tasks(cluster=cluster_arn, tasks=task_arns)

        if not task_details["tasks"]:
            raise ECSException("No ECS tasks returned.")
        container_details = task_details["tasks"][0]["containers"][0]
        if container_details.get("managedAgents", None):
            managed_agents = container_details["managedAgents"]
        else:
            raise ECSException("No managed agent on ecs task.")

        execute_command_agent = [
            agent for agent in managed_agents if agent["name"] == "ExecuteCommandAgent"
        ]
        if not execute_command_agent:
            raise ECSException("No ExecuteCommandAgent on ecs task.")
        return execute_command_agent[0]["lastStatus"] == "RUNNING"

    @wait_until(
        max_attempts=20,
        message_on_false="ECS task did not register in time",
    )
    def wait_for_task_to_register(self, cluster_arn: str, task_family: str) -> list[str]:
        task_arns = self.get_ecs_task_arns(cluster=cluster_arn, task_def_family=task_family)
        if task_arns:
            return task_arns
        return False

    def get_service_rollout_state(
        self, cluster_name: str, service_name: str, start_time: float
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Returns status & statusReason for the deployment of an ECS service.

        rolloutState can be: PENDING | SUCCESSFUL | STOPPED | STOP_REQUESTED | IN_PROGRESS | ROLLBACK_REQUESTED | ROLLBACK_IN_PROGRESS | ROLLBACK_SUCCESSFUL | ROLLBACK_FAILED
        """
        resp = self.ecs_client.list_service_deployments(
            cluster=cluster_name, service=service_name, createdAt={"after": start_time}
        )
        deployments = resp.get("serviceDeployments", [])

        if not deployments:
            return None, f"No deployments found for '{service_name}'"

        return deployments[0].get("status"), deployments[0].get("statusReason")

    def get_container_names_from_ecs_tasks(
        self, cluster_name: str, task_ids: list[str]
    ) -> list[str]:
        """Retrieve container names from each ECS task provided."""

        response = self.ecs_client.describe_tasks(cluster=cluster_name, tasks=task_ids)

        names = []
        for task in response.get("tasks", []):
            for container in task.get("containers", []):
                if container["name"] not in names:
                    names.append(container["name"])
        return names

    def register_task_definition(
        self,
        service: str,
        task_definition: dict,
        image_tag: Optional[str] = None,
    ) -> str:
        """Register a new task definition revision using provided model and
        containerDefinitions."""

        if image_tag:
            for container in task_definition["containerDefinitions"]:
                if container["name"] == service:
                    image_uri = container["image"].rsplit(":", 1)[0]
                    container["image"] = f"{image_uri}:{image_tag}"
                    break

        try:
            task_definition_response = self.ecs_client.register_task_definition(**task_definition)
            return task_definition_response["taskDefinition"]["taskDefinitionArn"]
        except ClientError as err:
            raise PlatformException(f"Error registering task definition: {err}")

    def update_service(
        self, service: str, task_def_arn: str, environment: str, application: str
    ) -> dict[str, Any]:
        """Update an ECS service and return the response."""

        try:
            service_response = self.ecs_client.update_service(
                cluster=f"{application}-{environment}-cluster",
                service=f"{application}-{environment}-{service}",
                taskDefinition=task_def_arn,
            )
            return service_response["service"]
        except ClientError as err:
            raise PlatformException(f"Error updating ECS service: {err}")
