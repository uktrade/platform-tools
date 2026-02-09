from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.terraform import TerraformProvider


class CDNDetach:
    def __init__(
        self,
        config_provider: ConfigProvider,
        terraform_environment: TerraformEnvironment,
        terraform_provider: TerraformProvider = None,
    ):
        self.config_provider = config_provider
        self.terraform_environment = terraform_environment
        self.terraform_provider = terraform_provider or TerraformProvider()

    def execute(self, environment_name, dry_run=True):
        config = self.config_provider.get_enriched_config()
        if environment_name not in config.get("environments", {}):
            raise PlatformException(
                f"cannot detach CDN resources for environment {environment_name}. It does not exist in your configuration"
            )

        # Populates ./terraform/environments/{environment_name}
        self.terraform_environment.generate(environment_name)
        terraform_config_dir = f"terraform/environments/{environment_name}"

        self.terraform_provider.init(terraform_config_dir)
        state = self.terraform_provider.pull_state(terraform_config_dir)
        self.filter_resources_to_detach(state)

        if not dry_run:
            raise NotImplementedError("--no-dry-run mode is not yet implemented")

    def filter_resources_to_detach(self, terraform_state):
        return [
            r
            for r in terraform_state["resources"]
            if r["mode"] == "managed"
            and r["provider"].endswith((".domain", ".domain-cdn"))
            and "module.extensions.module.alb" not in r["module"]
        ]
