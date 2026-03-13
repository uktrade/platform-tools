import datetime
import json
import re
from dataclasses import dataclass
from functools import cached_property

from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.s3 import S3Provider
from dbt_platform_helper.providers.terraform import TerraformProvider
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider


class CDNResourcesNotImportedException(PlatformException):
    def __init__(self, resources):
        self.resources = resources

    def __str__(self):
        msg = "The following resource(s) have not yet been imported into platform-public-ingress:"
        addresses = sorted(address_for_tfstate_resource(res) for res in self.resources)
        for address in addresses:
            msg += f"\n  {address}"
        return msg


@dataclass(frozen=True)
class CDNDetachLogic:
    platform_config: dict
    environment_name: str
    environment_tfstate: dict
    ingress_tfstate: dict

    @staticmethod
    def tfstate_resources(tfstate):
        return [
            {**resource_block, **instance}
            for resource_block in tfstate.get("resources", [])
            for instance in resource_block["instances"]
        ]

    @cached_property
    def environment_tfstate_resources(self):
        return self.tfstate_resources(self.environment_tfstate)

    @cached_property
    def ingress_tfstate_resources(self):
        return self.tfstate_resources(self.ingress_tfstate)

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

    @staticmethod
    def is_resource_importable(res):
        return res["type"] != "aws_acm_certificate_validation"

    @staticmethod
    def is_same_resource(res1, res2):
        if res1["type"] != res2["type"]:
            return False
        identity1 = res1.get("identity")
        identity2 = res2.get("identity")
        if identity1 and identity2:
            if res1["type"] == "aws_route53_record":
                identity1["name"] = identity1["name"].rstrip(".")
                identity2["name"] = identity2["name"].rstrip(".")
            return identity1 == identity2
        arn1 = res1.get("attributes", {}).get("arn")
        arn2 = res2.get("attributes", {}).get("arn")
        if arn1 and arn2:
            return arn1 == arn2
        if res1["type"] == "aws_cloudfront_monitoring_subscription":
            return res1["attributes"]["id"] == res2["attributes"]["id"]
        raise NotImplementedError(f"don't know how to compare resources of type {res1['type']}")

    def is_resource_in_ingress_tfstate(self, res):
        return any(
            self.is_same_resource(res, other_res) for other_res in self.ingress_tfstate_resources
        )

    @cached_property
    def resources_not_in_ingress_tfstate(self):
        return [
            res
            for res in self.resources_to_detach
            if self.is_resource_importable(res) and not self.is_resource_in_ingress_tfstate(res)
        ]


class CDNDetach:
    def __init__(
        self,
        io: ClickIOProvider,
        config_provider: ConfigProvider,
        s3_provider: S3Provider,
        terraform_environment: TerraformEnvironment,
        manifest_provider: TerraformManifestProvider = None,
        terraform_provider: TerraformProvider = None,
        logic_constructor=CDNDetachLogic,
    ):
        self.io = io
        self.config_provider = config_provider
        self.s3_provider = s3_provider
        self.terraform_environment = terraform_environment
        self.manifest_provider = manifest_provider or self.terraform_environment.manifest_provider
        self.terraform_provider = terraform_provider or TerraformProvider()
        self.logic_constructor = logic_constructor

    def execute(self, environment_name, dry_run=True, cdn_account_profile=None):
        run_timestamp = datetime.datetime.now(tz=datetime.timezone.utc)

        platform_config = self.config_provider.get_enriched_config()
        if environment_name not in platform_config.get("environments", {}):
            raise PlatformException(
                f"cannot detach CDN resources for environment {environment_name}. It does not exist in your configuration"
            )

        environment_tfstate = self.fetch_environment_tfstate(environment_name)
        ingress_tfstate = self.fetch_ingress_tfstate(environment_name, cdn_account_profile)

        logic_result = self.logic_constructor(
            platform_config=platform_config,
            environment_name=environment_name,
            environment_tfstate=environment_tfstate,
            ingress_tfstate=ingress_tfstate,
        )

        self.log_resources_to_detach(logic_result.resources_to_detach, environment_name)

        if logic_result.resources_not_in_ingress_tfstate:
            raise CDNResourcesNotImportedException(logic_result.resources_not_in_ingress_tfstate)

        if not dry_run:
            audit = AuditRecorder(
                config_provider=self.config_provider,
                s3_provider=self.s3_provider,
                environment_name=environment_name,
                run_timestamp=run_timestamp,
            )
            audit.record_environment_tfstate("before")
            audit.record_resources_removed(logic_result.resources_to_detach)

            if logic_result.resources_to_detach:
                self.io.info(
                    f"Removing resources from the {environment_name} environment's terraform state..."
                )
                terraform_config_dir = f"terraform/environments/{environment_name}"
                self.terraform_provider.remove_from_state(
                    terraform_config_dir,
                    {address_for_tfstate_resource(res) for res in logic_result.resources_to_detach},
                )

            audit.record_environment_tfstate("after")
            self.io.info("Success.")

    def fetch_environment_tfstate(self, environment_name):
        self.terraform_environment.generate(environment_name)
        terraform_config_dir = f"terraform/environments/{environment_name}"

        self.io.info(f"Fetching a copy of the {environment_name} environment's terraform state...")
        self.terraform_provider.init(terraform_config_dir)
        return self.terraform_provider.pull_state(terraform_config_dir)

    def fetch_ingress_tfstate(self, environment_name, cdn_account_profile=None):
        config = self.config_provider.get_enriched_config()
        application_name = config["application"]
        cdn_account_name = config["environments"][environment_name]["accounts"]["dns"]["name"]

        self.manifest_provider.generate_platform_public_ingress_config(
            application_name=application_name,
            environment_name=environment_name,
            cdn_account_name=cdn_account_name,
            cdn_account_profile=cdn_account_profile or cdn_account_name,
        )
        terraform_config_dir = (
            f"terraform/platform-public-ingress/{application_name}/{environment_name}"
        )

        self.io.info(
            f"Fetching a copy of the platform-public-ingress terraform state for {application_name}/{environment_name}..."
        )
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
        self.io.info("")


def address_for_tfstate_resource(res):
    s = res["module"] + "." + res["type"] + "." + res["name"]
    try:
        # XXX: does json.dumps escape special characters in strings the same way that terraform does?
        s += "[" + json.dumps(res["index_key"]) + "]"
    except KeyError:
        pass
    return s


class AuditRecorder:
    bucket_name = "platform-cdn-detach-audit"

    def __init__(self, config_provider, s3_provider, environment_name, run_timestamp):
        self.config_provider = config_provider
        self.s3_provider = s3_provider
        self.environment_name = environment_name
        self.run_timestamp = run_timestamp

    @property
    def application_name(self):
        return self.config_provider.get_enriched_config()["application"]

    @property
    def deploy_account_name(self):
        cfg = self.config_provider.get_enriched_config()
        return cfg["environments"][self.environment_name]["accounts"]["deploy"]["name"]

    @property
    def key_prefix(self):
        run_timestamp_str = self.run_timestamp.strftime("%Y-%m-%d/%H:%M:%S")
        return f"{self.application_name}/{self.environment_name}/{run_timestamp_str}"

    def record_environment_tfstate(self, before_or_after):
        self.s3_provider.copy_object(
            source_bucket_name=f"terraform-platform-state-{self.deploy_account_name}",
            source_object_key=f"tfstate/application/{self.application_name}-{self.environment_name}.tfstate",
            dest_bucket_name=self.bucket_name,
            dest_object_key=f"{self.key_prefix}/{before_or_after}.tfstate",
        )

    def record_resources_removed(self, resources):
        addresses = sorted(address_for_tfstate_resource(res) for res in resources)
        self.s3_provider.put_object(
            bucket_name=self.bucket_name,
            object_key=f"{self.key_prefix}/resources_removed.json",
            body=json.dumps(addresses, separators=(",", ":")),
        )
