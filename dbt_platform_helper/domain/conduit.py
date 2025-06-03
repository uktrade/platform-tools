from abc import ABC
from abc import abstractmethod
from typing import Callable
from typing import Optional

from dbt_platform_helper.providers.cloudformation import CloudFormation
from dbt_platform_helper.providers.copilot import _normalise_secret_name
from dbt_platform_helper.providers.copilot import connect_to_addon_client_task
from dbt_platform_helper.providers.copilot import create_addon_client_task
from dbt_platform_helper.providers.copilot import get_postgres_admin_connection_string
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.secrets import Secrets
from dbt_platform_helper.providers.vpc import VpcProvider
from dbt_platform_helper.utils.application import Application


class ConduitECSStrategy(ABC):
    @abstractmethod
    def get_data(self):
        pass

    @abstractmethod
    def start_task(self, data_context: dict):
        pass

    @abstractmethod
    def exec_task(self, data_context: dict):
        pass


class TerraformConduitStrategy(ConduitECSStrategy):
    def __init__(
        self,
        clients,
        ecs_provider: ECS,
        application: Application,
        addon_name: str,
        addon_type: str,
        access: str,
        env: str,
        io: ClickIOProvider,
        vpc_provider: Callable,
        get_postgres_admin_connection_string: Callable,
    ):
        self.clients = clients
        self.ecs_provider = ecs_provider
        self.io = io
        self.vpc_provider = vpc_provider
        self.access = access
        self.addon_name = addon_name
        self.addon_type = addon_type
        self.application = application
        self.env = env
        self.get_postgres_admin_connection_string = get_postgres_admin_connection_string

    def get_data(self):
        self.io.info("Starting conduit in Terraform mode.")
        return {
            "cluster_arn": self.ecs_provider.get_cluster_arn_by_name(
                f"{self.application.name}-{self.env}"
            ),
            "task_def_family": self._generate_container_name(),
            "vpc_name": self._resolve_vpc_name(),
            "addon_type": self.addon_type,
            "access": self.access,
        }

    def start_task(self, data_context: dict):

        environments = self.application.environments
        environment = environments.get(self.env)
        env_session = environment.session

        vpc_provider = self.vpc_provider(env_session)
        vpc_config = vpc_provider.get_vpc(
            self.application.name,
            self.env,
            data_context["vpc_name"],
        )

        postgres_admin_env_vars = None
        if data_context["addon_type"] == "postgres" and data_context["access"] == "admin":
            postgres_admin_env_vars = [
                {
                    "name": "CONNECTION_SECRET",
                    "value": self.get_postgres_admin_connection_string(
                        self.clients.get("ssm"),
                        f"/copilot/{self.application.name}/{self.env}/secrets/{_normalise_secret_name(self.addon_name)}",
                        self.application,
                        self.env,
                        self.addon_name,
                    ),
                },
            ]

        self.ecs_provider.start_ecs_task(
            f"{self.application.name}-{self.env}",
            self._generate_container_name(),
            data_context["task_def_family"],
            vpc_config,
            postgres_admin_env_vars,
        )

    def exec_task(self, data_context: dict):
        self.ecs_provider.exec_task(data_context["cluster_arn"], data_context["task_arns"][0])

    def _generate_container_name(self):
        return f"conduit-{self.addon_type}-{self.access}-{self.application.name}-{self.env}-{self.addon_name}"

    def _resolve_vpc_name(self):
        ssm_client = self.clients["ssm"]
        parameter_key = f"/conduit/{self.application.name}/{self.env}/{_normalise_secret_name(self.addon_name)}_VPC_NAME"

        try:
            response = ssm_client.get_parameter(Name=parameter_key)
            return response["Parameter"]["Value"]
        except ssm_client.exceptions.ParameterNotFound:
            self.io.abort_with_error(
                f"Could not find VPC name for {self.addon_name}. Missing SSM param: {parameter_key}"
            )


class CopilotConduitStrategy(ConduitECSStrategy):
    def __init__(
        self,
        clients,
        ecs_provider: ECS,
        secrets_provider: Secrets,
        cloudformation_provider: CloudFormation,
        application: Application,
        addon_name: str,
        access: str,
        env: str,
        io: ClickIOProvider,
        connect_to_addon_client_task: Callable,
        create_addon_client_task: Callable,
    ):
        self.clients = clients
        self.cloudformation_provider = cloudformation_provider
        self.ecs_provider = ecs_provider
        self.secrets_provider = secrets_provider

        self.io = io
        self.access = access
        self.addon_name = addon_name
        self.application = application
        self.env = env
        self.connect_to_addon_client_task = connect_to_addon_client_task
        self.create_addon_client_task = create_addon_client_task

    def get_data(self):

        addon_type = self.secrets_provider.get_addon_type(self.addon_name)
        parameter_name = self.secrets_provider.get_parameter_name(
            addon_type, self.addon_name, self.access
        )
        task_name = self.ecs_provider.get_or_create_task_name(self.addon_name, parameter_name)

        return {
            "cluster_arn": self.ecs_provider.get_cluster_arn_by_copilot_tag(),
            "addon_type": addon_type,
            "task_def_family": f"copilot-{task_name}",
            "parameter_name": parameter_name,
            "task_name": task_name,
        }

    def start_task(self, data_context: dict):
        self.create_addon_client_task(
            self.clients["iam"],
            self.clients["ssm"],
            self.application,
            self.env,
            data_context["addon_type"],
            self.addon_name,
            data_context["task_name"],
            self.access,
        )

        self.io.info("Updating conduit task")
        self.cloudformation_provider.add_stack_delete_policy_to_task_role(data_context["task_name"])
        stack_name = self.cloudformation_provider.update_conduit_stack_resources(
            self.application.name,
            self.env,
            data_context["addon_type"],
            self.addon_name,
            data_context["task_name"],
            data_context["parameter_name"],
            self.access,
        )
        self.io.info("Waiting for conduit task update to complete...")
        self.cloudformation_provider.wait_for_cloudformation_to_reach_status(
            "stack_update_complete", stack_name
        )

    def exec_task(self, data_context: dict):
        self.connect_to_addon_client_task(
            self.clients["ecs"],
            self.application.name,
            self.env,
            data_context["cluster_arn"],
            data_context["task_name"],
        )


class ConduitStrategyFactory:

    @staticmethod
    def detect_mode(
        ecs_client,
        application,
        environment,
        addon_name: str,
        addon_type: str,
        access: str,
        io: ClickIOProvider,
    ) -> str:
        """Detect if Terraform-based conduit task definitions are present,
        otherwise default to Copilot mode."""
        paginator = ecs_client.get_paginator("list_task_definitions")
        prefix = f"conduit-{addon_type}-{access}-{application}-{environment}-{addon_name}"

        for page in paginator.paginate():
            for arn in page["taskDefinitionArns"]:
                if arn.split("/")[-1].startswith(prefix):
                    return "terraform"

        io.info("Defaulting to copilot mode.")
        return "copilot"

    @staticmethod
    def create_strategy(
        mode: str,
        clients,
        ecs_provider: ECS,
        secrets_provider: Secrets,
        cloudformation_provider: CloudFormation,
        application: Application,
        addon_name: str,
        addon_type: str,
        access: str,
        env: str,
        io: ClickIOProvider,
    ):

        if mode == "terraform":
            return TerraformConduitStrategy(
                clients,
                ecs_provider,
                application,
                addon_name,
                addon_type,
                access,
                env,
                io,
                vpc_provider=VpcProvider,
                get_postgres_admin_connection_string=get_postgres_admin_connection_string,
            )
        else:
            return CopilotConduitStrategy(
                clients,
                ecs_provider,
                secrets_provider,
                cloudformation_provider,
                application,
                addon_name,
                access,
                env,
                io,
                connect_to_addon_client_task=connect_to_addon_client_task,
                create_addon_client_task=create_addon_client_task,
            )


class Conduit:
    def __init__(
        self,
        application: Application,
        secrets_provider: Secrets,
        cloudformation_provider: CloudFormation,
        ecs_provider: ECS,
        io: ClickIOProvider = ClickIOProvider(),
        vpc_provider=VpcProvider,
        strategy_factory: Optional[ConduitStrategyFactory] = None,
    ):

        self.application = application
        self.secrets_provider = secrets_provider
        self.cloudformation_provider = cloudformation_provider
        self.ecs_provider = ecs_provider
        self.io = io
        self.vpc_provider = vpc_provider
        self.strategy_factory = strategy_factory or ConduitStrategyFactory()

    def start(self, env: str, addon_name: str, access: str = "read"):
        self.clients = self._initialise_clients(env)
        addon_type = self.secrets_provider.get_addon_type(addon_name)

        if (addon_type == "opensearch" or addon_type == "redis") and (access != "read"):
            access = "read"

        mode = self.strategy_factory.detect_mode(
            self.clients.get("ecs"),
            self.application.name,
            env,
            addon_name,
            addon_type,
            access,
            self.io,
        )

        strategy = self.strategy_factory.create_strategy(
            mode=mode,
            clients=self.clients,
            ecs_provider=self.ecs_provider,
            secrets_provider=self.secrets_provider,
            cloudformation_provider=self.cloudformation_provider,
            application=self.application,
            addon_name=addon_name,
            addon_type=addon_type,
            access=access,
            env=env,
            io=self.io,
        )

        data_context = strategy.get_data()

        data_context["task_arns"] = self.ecs_provider.get_ecs_task_arns(
            data_context["cluster_arn"], data_context["task_def_family"]
        )

        info_log = (
            f"Checking if a conduit ECS task is already running for:\n"
            f"  Addon Name : {addon_name}\n"
            f"  Addon Type : {addon_type}"
        )

        if addon_type == "postgres":
            info_log += f"\n  Access Level : {access}"

        self.io.info(info_log)

        if not data_context["task_arns"]:
            self.io.info("Creating conduit ECS task...")
            strategy.start_task(data_context)
            data_context["task_arns"] = self.ecs_provider.wait_for_task_to_register(
                data_context["cluster_arn"], data_context["task_def_family"]
            )
        else:
            self.io.info(f"Found a task already running: {data_context['task_arns'][0]}")

        self.io.info(f"Waiting for ECS Exec agent to become available on the conduit task...")
        self.ecs_provider.ecs_exec_is_available(
            data_context["cluster_arn"], data_context["task_arns"]
        )

        self.io.info("Connecting to conduit task...")
        strategy.exec_task(data_context)

    def _initialise_clients(self, env):
        return {
            "ecs": self.application.environments[env].session.client("ecs"),
            "iam": self.application.environments[env].session.client("iam"),
            "ssm": self.application.environments[env].session.client("ssm"),
        }
