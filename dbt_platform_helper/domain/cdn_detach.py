from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment


class CDNDetach:
    def __init__(
        self,
        terraform_environment: TerraformEnvironment,
    ):
        self.terraform_environment = terraform_environment

    def execute(self, environment_name):
        self.terraform_environment.generate(environment_name)
