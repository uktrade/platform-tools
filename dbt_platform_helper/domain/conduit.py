from abc import ABC
from abc import abstractmethod

from dbt_platform_helper.providers.cloudformation import CloudFormation
from dbt_platform_helper.providers.copilot import _normalise_secret_name
from dbt_platform_helper.providers.copilot import connect_to_addon_client_task
from dbt_platform_helper.providers.copilot import create_addon_client_task
from dbt_platform_helper.providers.copilot import get_postgres_admin_connection_string
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.secrets import Secrets
from dbt_platform_helper.providers.vpc import VpcProvider
from dbt_platform_helper.providers.vpc import VpcProviderException
from dbt_platform_helper.utils.application import Application


class ConduitECSStrategy(ABC):
    @abstractmethod
    def get_data(self):
        pass

    @abstractmethod
    def start_task(self, data_context):
        pass

    @abstractmethod
    def exec_task(self, data_context):
        pass


class TerraformConduitStrategy(ConduitECSStrategy):
    def __init__(
        self,
        clients,
        ecs_provider: ECS,
        application: Application,
        addon_name: str,
        access: str,
        env: str,
        io: ClickIOProvider = ClickIOProvider(),
        vpc_provider=VpcProvider,
        get_postgres_admin_connection_string=get_postgres_admin_connection_string,
    ):
        self.clients = clients
        self.ecs_provider = ecs_provider
        self.io = io
        self.vpc_provider = vpc_provider
        self.access = access
        self.addon_name = addon_name
        self.application = application
        self.env = env
        self.get_postgres_admin_connection_string = get_postgres_admin_connection_string

    def get_data(self):
        self.io.info("Starting ECS task using Terraform-defined task definition.")
        return {
            "cluster_arn": self.ecs_provider.get_cluster_arn_by_name(
                f"{self.application.name}-{self.env}-tf"
            ),
            "task_def_family": f"conduit-{self.application.name}-{self.env}-{self.addon_name}",
            "vpc_name": "platform-sandbox-dev",  # TODO update hard coding
        }

    def start_task(self, data_context):

        environments = self.application.environments
        environment = environments.get(self.env)
        env_session = environment.session
        try:
            vpc_provider = self.vpc_provider(env_session)
            vpc_config = vpc_provider.get_vpc(
                self.application.name,
                self.env,
                data_context["vpc_name"],
            )
        except VpcProviderException as ex:
            self.io.abort_with_error(str(ex))

        self.ecs_provider.start_ecs_task(
            f"conduit-{self.application.name}-{self.env}-{self.addon_name}",
            data_context["task_def_family"],
            vpc_config,
            [
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
            ],
        )

    def exec_task(self, data_context):
        self.ecs_provider.exec_task(data_context["cluster_arn"], data_context["task_arns"][0])


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
        io: ClickIOProvider = ClickIOProvider(),
        connect_to_addon_client_task=connect_to_addon_client_task,
        create_addon_client_task=create_addon_client_task,
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

        self.io.info(f"Checking if a conduit task is already running for {addon_type}")

        return {
            "cluster_arn": self.ecs_provider.get_cluster_ar_by_copilot_tag(),
            "addon_type": addon_type,
            "task_def_family": f"copilot-{task_name}",
            "parameter_name": parameter_name,
            "task_name": task_name,
        }

    def start_task(self, data_context):
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

    def exec_task(self, data_context):
        self.connect_to_addon_client_task(
            self.clients["ecs"],
            self.application.name,
            self.env,
            data_context["cluster_arn"],
            data_context["task_name"],
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
    ):

        self.application = application
        self.secrets_provider = secrets_provider
        self.cloudformation_provider = cloudformation_provider
        self.ecs_provider = ecs_provider
        self.io = io
        self.vpc_provider = vpc_provider

    def start(self, env: str, addon_name: str, access: str = "read"):
        self.clients = self._initialise_clients(env)
        mode = self._detect_mode(self.application.name, env, addon_name)

        if mode == "terraform":
            strategy = TerraformConduitStrategy(
                self.clients,
                self.ecs_provider,
                self.application,
                addon_name,
                access,
                env,
            )
        else:
            strategy = CopilotConduitStrategy(
                self.clients,
                self.ecs_provider,
                self.secrets_provider,
                self.cloudformation_provider,
                self.application,
                addon_name,
                access,
                env,
            )

        data_context = strategy.get_data()

        data_context["task_arns"] = self.ecs_provider.get_ecs_task_arns(
            data_context["cluster_arn"], data_context["task_def_family"]
        )

        if not data_context["task_arns"]:
            self.io.info("Creating conduit task")
            strategy.start_task(data_context)
            data_context["task_arns"] = self.ecs_provider.get_ecs_task_arns(
                data_context["cluster_arn"], data_context["task_def_family"]
            )
        else:
            self.io.info("Conduit task already running")

        self.io.info(f"Checking if exec is available for conduit task...")

        self.ecs_provider.ecs_exec_is_available(
            data_context["cluster_arn"], data_context["task_arns"]
        )

        self.io.info("Connecting to conduit task")
        strategy.exec_task(data_context)

    def _detect_mode(self, application, environment, addon_name: str) -> str:
        paginator = self.clients.get("ecs").get_paginator("list_task_definitions")
        prefix = f"conduit-{application}-{environment}-{addon_name}"

        for page in paginator.paginate():
            for arn in page["taskDefinitionArns"]:
                if arn.split("/")[-1].startswith(prefix):
                    self.io.info(f"Detected Terraform-defined ECS task definition: {arn}")
                    return "terraform"

        self.io.info("Defaulting to copilot mode.")
        return "copilot"

    def _initialise_clients(self, env):
        return {
            "ecs": self.application.environments[env].session.client("ecs"),
            "iam": self.application.environments[env].session.client("iam"),
            "ssm": self.application.environments[env].session.client("ssm"),
        }
