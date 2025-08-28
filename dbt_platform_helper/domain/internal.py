from dbt_platform_helper.entities.service import ServiceConfig
from dbt_platform_helper.providers.config import ConfigLoader
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.utils.application import load_application


class Internal:

    def __init__(
        self,
        ecs_provider=ECS,
        load_application=load_application,
        config_provider=ConfigProvider(ConfigValidator()),
        loader: ConfigLoader = ConfigLoader(),
    ):
        self.ecs_provider = ecs_provider
        self.load_application = load_application
        self.config_provider = config_provider
        self.loader = loader

    def deploy(self, service: str, environment: str, application: str, image_tag: str = None):

        task_def = self.ecs_provider.get_task_definition_arn(
            application=application, environment=environment, service=service
        )
        service_config = self.loader.load_into_model(
            f"terraform/services/{environment}/{service}/service-config.yml",
            ServiceConfig,
        )
        print(f"service config name: {service_config.name}")
        if task_def:
            # Register new revision
            print(f"found task def {task_def}")
        else:
            # Create new task definition
            print(f"found no task def")

        cluster_name = f"{application}-{environment}-cluster"
        ecs_service = self.ecs_provider.get_ecs_service_arn(
            cluster_name=cluster_name, service_name=service
        )
        if ecs_service:
            # Update existing ecs service
            print(f"found ecs service {ecs_service}")
        else:
            # Create new ecs service
            print(f"found no ecs service")

    def delete(self, service: str, environment: str, application: str):
        pass
