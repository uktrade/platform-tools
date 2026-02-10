import json

from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.terraform import TerraformProvider


class CDNDetach:
    def __init__(
        self,
        io: ClickIOProvider,
        config_provider: ConfigProvider,
        terraform_environment: TerraformEnvironment,
        terraform_provider: TerraformProvider = None,
    ):
        self.io = io
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

        self.io.info(f"Fetching a copy of the {environment_name} environment's terraform state...")
        self.terraform_provider.init(terraform_config_dir)
        state = self.terraform_provider.pull_state(terraform_config_dir)

        resources = self.get_resources_to_detach(state)
        self.log_resources_to_detach(resources, environment_name)

        if not dry_run:
            raise NotImplementedError("--no-dry-run mode is not yet implemented")

    def get_resources_to_detach(self, terraform_state):
        return [
            r
            for r in terraform_state["resources"]
            if r["mode"] == "managed"
            and r["provider"].endswith((".domain", ".domain-cdn"))
            and "module.extensions.module.alb" not in r["module"]
        ]

    def log_resources_to_detach(self, resources, environment_name):
        self.io.info("")
        self.io.info(
            f"Will remove the following resources from the {environment_name} environment's terraform state:"
        )
        for address in sorted(self.iter_addresses_for_resources(resources)):
            self.io.info(f"  {address}")

    def iter_addresses_for_resources(self, resources):
        for resource in resources:
            base = ".".join((resource["module"], resource["type"], resource["name"]))
            instances = resource["instances"]
            if len(instances) == 1 and "index_key" not in instances[0]:
                yield base
            else:
                for instance in instances:
                    # XXX: does json.dumps escape special characters in strings the same way that terraform does?
                    yield base + "[" + json.dumps(instance["index_key"]) + "]"
