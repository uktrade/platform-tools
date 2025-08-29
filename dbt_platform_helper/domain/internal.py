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

        print(f"task def successfully created: {service_config}")

        service_model = self.loader.load_into_model(service_config, ServiceConfig)

        task_def_arn = self.ecs_provider.register_task_definition(
            service_model, environment, application
        )
        print(task_def_arn)

        cluster_name = f"{application}-{environment}-cluster"
        ecs_service = self.ecs_provider.get_ecs_service_arn(
            cluster_name=cluster_name, service_name=service_model.name
        )
        if ecs_service:
            # Update existing ecs service
            print(f"found ecs service {ecs_service}")
        else:
            # Create new ecs service
            print(f"found no ecs service")

    def delete(self, service: str, environment: str, application: str):
        pass
