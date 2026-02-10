import json
import re

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

        resources = self.get_resources_to_detach(state, environment_name)
        self.log_resources_to_detach(resources, environment_name)

        if not dry_run:
            raise NotImplementedError("--no-dry-run mode is not yet implemented")

    def get_resources_to_detach(self, terraform_state, environment_name):
        result = []
        for resource in terraform_state["resources"]:
            if not self.resource_is_detachable(resource):
                continue
            m = re.match(r'^module\.extensions\.module\.\w+\["([^"]+)"\]', resource["module"])
            extension_name = m.group(1)
            if not self.extension_has_managed_ingress(extension_name, environment_name):
                # This resource is due for detach, but it will not actually be detached until the
                # managed_ingress option of the extension that owns it gets set to true.
                continue
            result.append(resource)
        return result

    @staticmethod
    def resource_is_detachable(resource):
        return (
            resource["mode"] == "managed"
            and resource["provider"].endswith((".domain", ".domain-cdn"))
            and "module.extensions.module.alb" not in resource["module"]
        )

    def extension_has_managed_ingress(self, extension_name, environment_name):
        config = self.config_provider.get_enriched_config()
        ext_config = config["extensions"][extension_name]
        flattened_ext_config = {
            **ext_config,
            **(ext_config.get("environments", {}).get("*") or {}),
            **(ext_config.get("environments", {}).get(environment_name) or {}),
        }
        return flattened_ext_config.get("managed_ingress", False)

    def log_resources_to_detach(self, resources, environment_name):
        self.io.info("")
        if resources:
            self.io.info(
                f"Will remove the following resources from the {environment_name} environment's terraform state:"
            )
            for address in sorted(self.iter_addresses_for_resources(resources)):
                self.io.info(f"  {address}")
        else:
            self.io.info(
                f"Will not remove any resources from the {environment_name} environment's terraform state."
            )

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
