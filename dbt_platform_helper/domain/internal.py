from dbt_platform_helper.entities.service import ServiceConfig
from dbt_platform_helper.providers.config import ConfigLoader
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.providers.yaml_file import YamlFileProvider
from dbt_platform_helper.utils.application import load_application


class Internal:

    def __init__(
        self,
        ecs_provider: ECS,
        load_application=load_application,
        config_provider=ConfigProvider(ConfigValidator()),
        loader: ConfigLoader = ConfigLoader(),
    ):
        self.environment_variable_provider = None
        self.ecs_provider = ecs_provider
        self.load_application = load_application
        self.config_provider = config_provider
        self.loader = loader

    def deploy(self, service: str, environment: str, application: str):

        service_config = YamlFileProvider.load(
            f"terraform/services/{environment}/{service}/service-config.yml"
        )
        service_model = self.loader.load_into_model(service_config, ServiceConfig)

        task_def_arn = self.ecs_provider.register_task_definition(
            service_model, environment, application
        )
        print(f"Task definition successfully created: {task_def_arn}")

        service_arn = self.ecs_provider.update_service(
            service_model, task_def_arn, environment, application
        )

        print(f"Service successfully updated: {service_arn}")

    def delete(self, service: str, environment: str, application: str):
        pass
