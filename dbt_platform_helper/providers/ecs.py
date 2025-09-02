import random
import string
import subprocess
from typing import List
from typing import Optional

from dbt_platform_helper.entities.service import ServiceConfig
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
        env_vars: List[dict] = None,
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

    def get_ecs_task_arns(self, cluster_arn: str, task_def_family: str):
        """Gets the ECS task ARNs for a given task name and cluster ARN."""
        tasks = self.ecs_client.list_tasks(
            cluster=cluster_arn,
            desiredStatus="RUNNING",
            family=task_def_family,
        )

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
    def ecs_exec_is_available(self, cluster_arn: str, task_arns: List[str]) -> bool:
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
        task_arns = self.get_ecs_task_arns(cluster_arn, task_family)
        if task_arns:
            return task_arns
        return False

    def get_ecs_service_arn(self, cluster_name: str, service_name: str) -> Optional[str]:
        response = self.ecs_client.describe_services(
            cluster=cluster_name, services=[service_name]  # Search for a single service
        )
        service = response.get("services", [])
        if not service or service[0].get("status") == "INACTIVE":
            return None
        return service[0]["serviceArn"]

    def register_task_definition(
        self, service_model: ServiceConfig, environment: str, application: str
    ):
        container_definitions = []

        # This is the same for main service and sidecars
        default_config = {
            "mountPoints": [{"sourceVolume": "temporary-fs", "containerPath": "/tmp"}],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": f"/platform/ecs/service/{application}/{environment}/{service_model.name}",
                    "awslogs-region": "eu-west-2",
                    "awslogs-stream-prefix": "terraform",
                },
            },
        }

        # Main service definition
        service_definition = {
            "name": service_model.name,
            "image": service_model.image.location,
            "essential": True,
            "environment": [
                {"name": key, "value": str(value)}
                for key, value in (service_model.variables or {}).items()
            ],
            "secrets": [
                {"name": key, "valueFrom": value}
                for key, value in (service_model.secrets or {}).items()
            ],
        }

        if service_model.storage:
            service_definition["readonlyRootFilesystem"] = service_model.storage.readonly_fs

        if service_model.type == "Load Balanced Web Service":
            service_definition["portMappings"] = [
                {"containerPort": service_model.image.port, "protocol": "tcp"}
            ]

        if service_model.type == "Backend Service":
            service_definition["entryPoint"] = [
                entrypoint for entrypoint in service_model.entrypoint
            ]

        container_definitions.append(service_definition | default_config)

        # Add sidecars
        for sidecar_name, sidecar_config in (service_model.sidecars or {}).items():
            sidecar_definition = {
                "name": sidecar_name,
                "image": sidecar_config.image,
                "essential": (
                    True if (sidecar_config.essential is None) else sidecar_config.essential
                ),
                "environment": [
                    {"name": key, "value": str(value)}
                    for key, value in (sidecar_config.variables or {}).items()
                ],
                "secrets": [
                    {"name": key, "valueFrom": value}
                    for key, value in (sidecar_config.secrets or {}).items()
                ],
                "portMappings": [
                    {
                        "containerPort": sidecar_config.port,
                        "hostPort": sidecar_config.port,
                        "protocol": "tcp",
                    }
                ],
            }

            if (
                service_model.type == "Load Balanced Web Service"
                and service_model.http.target_container == sidecar_name
            ):
                sidecar_definition["portMappings"][0]["name"] = "target"

            container_definitions.append(sidecar_definition | default_config)

        # Register task definition
        try:
            task_definition_response = self.ecs_client.register_task_definition(
                family=f"{application}-{environment}-{service_model.name}-task-def",
                taskRoleArn=f"arn:aws:iam::563763463626:role/{application}-{environment}-{service_model.name}-ecs-task-role",  # TODO - Remove account id hardcoding
                executionRoleArn=f"arn:aws:iam::563763463626:role/{application}-{environment}-{service_model.name}-ecs-task-execution-role",  # TODO - Remove account id hardcoding
                networkMode="awsvpc",
                containerDefinitions=container_definitions,
                volumes=[{"name": "temporary-fs", "host": {}}],
                placementConstraints=[],
                requiresCompatibilities=["FARGATE"],
                cpu=str(service_model.cpu),
                memory=str(service_model.memory),
                tags=[
                    {"key": "application", "value": application},
                    {"key": "environment", "value": environment},
                    {"key": "service", "value": service_model.name},
                    {"key": "Managed-by", "value": "Platform Helper"},
                ],
            )
            return task_definition_response["taskDefinition"]["taskDefinitionArn"]
        except PlatformException as err:
            print(f"Error registering task definition: {err}")

    def update_service(
        self, service_model: ServiceConfig, task_def_arn: str, environment: str, application: str
    ):
        try:
            service_response = self.ecs_client.update_service(
                cluster=f"{application}-{environment}-cluster",
                service=f"{application}-{environment}-{service_model.name}",
                desiredCount=service_model.count,
                taskDefinition=task_def_arn,
                healthCheckGracePeriodSeconds=int(
                    service_model.http.healthcheck.grace_period.replace("s", "")
                ),
            )
            return service_response["service"]["serviceArn"]
        except PlatformException as err:
            print(f"Error updating ECS service: {err}")
