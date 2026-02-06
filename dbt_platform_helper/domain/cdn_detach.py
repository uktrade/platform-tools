from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.providers.terraform_state import TerraformStateProvider


class CDNDetach:
    def __init__(
        self,
        terraform_environment: TerraformEnvironment,
        terraform_state_provider: TerraformStateProvider = None,
    ):
        self.terraform_environment = terraform_environment
        self.terraform_state_provider = terraform_state_provider or TerraformStateProvider()

    def execute(self, environment_name, dry_run=True):
        # Populates ./terraform/environments/{environment_name}
        self.terraform_environment.generate(environment_name)

        self.terraform_state_provider.pull(f"terraform/environments/{environment_name}")

        if not dry_run:
            raise NotImplementedError("--no-dry-run mode is not yet implemented")
