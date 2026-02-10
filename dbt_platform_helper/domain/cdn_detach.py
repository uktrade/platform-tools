import json
import re
from dataclasses import dataclass
from functools import cached_property

from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.terraform import TerraformProvider


@dataclass(frozen=True)
class CDNDetachLogic:
    platform_config: dict
    environment_name: str
    environment_tfstate: dict

    @cached_property
    def environment_tfstate_resources(self):
        return [
            {**resource_block, **instance}
            for resource_block in self.environment_tfstate["resources"]
            for instance in resource_block["instances"]
        ]

    @staticmethod
    def is_resource_detachable(res):
        return (
            res["mode"] == "managed"
            and res["provider"].endswith((".domain", ".domain-cdn"))
            and "module.extensions.module.alb" not in res["module"]
        )

    @staticmethod
    def extension_name_for_resource(res):
        return re.match(r'^module\.extensions\.module\.\w+\["([^"]+)"\]', res["module"]).group(1)

    @cached_property
    def extensions_to_detach(self):
        """The set of extension names for which managed_ingress is set to
        true."""
        result = set()
        for ext_name, ext_config in self.platform_config.get("extensions", {}).items():
            flattened_ext_config = {
                **ext_config,
                **(ext_config.get("environments", {}).get("*") or {}),
                **(ext_config.get("environments", {}).get(self.environment_name) or {}),
            }
            if flattened_ext_config.get("managed_ingress", False):
                result.add(ext_name)
        return result

    @cached_property
    def resources_to_detach(self):
        """The list of tfstate resources that are intended to be detached in
        this session."""
        return [
            res
            for res in self.environment_tfstate_resources
            if self.is_resource_detachable(res)
            and self.extension_name_for_resource(res) in self.extensions_to_detach
        ]


class CDNDetach:
    def __init__(
        self,
        io: ClickIOProvider,
        config_provider: ConfigProvider,
        terraform_environment: TerraformEnvironment,
        terraform_provider: TerraformProvider = None,
        logic_constructor=CDNDetachLogic,
    ):
        self.io = io
        self.config_provider = config_provider
        self.terraform_environment = terraform_environment
        self.terraform_provider = terraform_provider or TerraformProvider()
        self.logic_constructor = logic_constructor

    def execute(self, environment_name, dry_run=True):
        platform_config = self.config_provider.get_enriched_config()
        if environment_name not in platform_config.get("environments", {}):
            raise PlatformException(
                f"cannot detach CDN resources for environment {environment_name}. It does not exist in your configuration"
            )

        environment_tfstate = self.fetch_environment_tfstate(environment_name)

        logic_result = self.logic_constructor(
            platform_config=platform_config,
            environment_name=environment_name,
            environment_tfstate=environment_tfstate,
        )

        self.log_resources_to_detach(logic_result.resources_to_detach, environment_name)

        if not dry_run:
            raise NotImplementedError("--no-dry-run mode is not yet implemented")

    def fetch_environment_tfstate(self, environment_name):
        self.terraform_environment.generate(environment_name)
        terraform_config_dir = f"terraform/environments/{environment_name}"

        self.io.info(f"Fetching a copy of the {environment_name} environment's terraform state...")
        self.terraform_provider.init(terraform_config_dir)
        return self.terraform_provider.pull_state(terraform_config_dir)

    def log_resources_to_detach(self, resources, environment_name):
        self.io.info("")
        if resources:
            self.io.info(
                f"Will remove the following resources from the {environment_name} environment's terraform state:"
            )
            addresses = sorted(address_for_tfstate_resource(res) for res in resources)
            for address in addresses:
                self.io.info(f"  {address}")
        else:
            self.io.info(
                f"Will not remove any resources from the {environment_name} environment's terraform state."
            )


def address_for_tfstate_resource(res):
    s = res["module"] + "." + res["type"] + "." + res["name"]
    try:
        # XXX: does json.dumps escape special characters in strings the same way that terraform does?
        s += "[" + json.dumps(res["index_key"]) + "]"
    except KeyError:
        pass
    return s
