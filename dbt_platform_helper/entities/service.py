from typing import ClassVar

from pydantic import BaseModel
from pydantic import Field


class ServiceConfig(BaseModel):
    name: str = Field(description="""Name of the Service.""")
    type: str = Field(description="""The type of service""")

    local_terraform_source: ClassVar[str] = "../../../../../platform-tools/terraform/ecs-service"

    # def add_locals(self, terraform, environment, image_tag):
    #     terraform["locals"] = {
    #         "environment": environment,
    #         "image_tag" : image_tag,
    #         "platform_config": "${yamldecode(file(\"../../../../platform-config.yml\"))}",
    #         "application": "${local.platform_config[\"application\"]}",
    #         "environments": "${local.platform_config[\"environments\"]}",
    #         "env_config": "${{for name, config in local.environments: name => merge(lookup(local.environments, \"*\", {}), config)}}",
    #         "service_config": "${yamldecode(templatefile(\"./service-config.yml\", {COPILOT_ENVIRONMENT_NAME = local.environment, IMAGE_TAG = local.image_tag}))}",
    #         "raw_env_config": "${local.platform_config[\"environments\"]}",
    #         "combined_env_config": "${{for name, config in local.raw_env_config: name => merge(lookup(local.raw_env_config, \"*\", {}), config)}}",
    #         "service_deployment_mode": "${lookup(local.combined_env_config[local.environment], \"service-deployment-mode\", \"copilot\")}",
    #         "non_copilot_service_deployment_mode": "${local.service_deployment_mode == \"dual-deploy-copilot-traffic\" || local.service_deployment_mode == \"dual-deploy-platform-traffic\" || local.service_deployment_mode == \"platform\" ? 1 : 0}"
    #     }
