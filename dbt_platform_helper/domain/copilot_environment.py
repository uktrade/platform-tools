from collections import defaultdict
from pathlib import Path

from boto3 import Session

from dbt_platform_helper.domain.terraform_environment import (
    EnvironmentNotFoundException,
)
from dbt_platform_helper.providers.cloudformation import CloudFormation
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.load_balancers import LoadBalancerProvider
from dbt_platform_helper.providers.vpc import Vpc
from dbt_platform_helper.providers.vpc import VpcNotFoundForNameException
from dbt_platform_helper.providers.vpc import VpcProvider
from dbt_platform_helper.utils.template import S3_CROSS_ACCOUNT_POLICY
from dbt_platform_helper.utils.template import camel_case
from dbt_platform_helper.utils.template import setup_templates


class CopilotEnvironment:
    def __init__(
        self,
        config_provider: ConfigProvider,
        vpc_provider: VpcProvider = None,
        cloudformation_provider: CloudFormation = None,
        session: Session = None,  # TODO: DBTP-1954: - this is a temporary fix, will fall away once _get_environment_vpc is updated.
        copilot_templating=None,
        io: ClickIOProvider = ClickIOProvider(),
        load_balancer_provider: LoadBalancerProvider = LoadBalancerProvider,
    ):
        self.config_provider = config_provider
        self.vpc_provider = vpc_provider
        self.copilot_templating = copilot_templating or CopilotTemplating(
            file_provider=FileProvider(),
        )
        self.io = io
        self.session = session
        self.load_balancer = load_balancer_provider(session)
        self.cloudformation_provider = cloudformation_provider

    def generate(self, environment_name: str) -> None:

        platform_config = self.config_provider.get_enriched_config()

        if environment_name not in platform_config.get("environments").keys():
            raise EnvironmentNotFoundException(
                f"Error: cannot generate copilot manifests for environment {environment_name}.  It does not exist in your configuration"
            )

        env_config = platform_config["environments"][environment_name]
        profile_for_environment = env_config.get("accounts", {}).get("deploy", {}).get("name")

        self.io.info(f"Using {profile_for_environment} for this AWS session")

        app_name = platform_config["application"]

        certificate_arn = self.load_balancer.get_https_certificate_for_application(
            app_name, environment_name
        )

        vpc = self._get_environment_vpc(
            self.session, app_name, environment_name, env_config.get("vpc", None)
        )

        copilot_environment_manifest = self.copilot_templating.generate_copilot_environment_manifest(
            environment_name=environment_name,
            # We need to correct the subnet id order before adding it to the template. See pydoc on below method for details.
            vpc=self._match_subnet_id_order_to_cloudformation_exports(environment_name, vpc),
            cert_arn=certificate_arn,
        )

        self.io.info(
            self.copilot_templating.write_environment_manifest(
                environment_name, copilot_environment_manifest
            )
        )

    # TODO: DBTP-1954: There should always be a vpc_name as defaults have been applied to the config.  This function can
    # probably fall away. We shouldn't need to check 3 different names (vpc_name, session.profile_name, {session.profile_name}-{env_name})
    # To be checked.
    def _get_environment_vpc(self, session: Session, app_name, env_name: str, vpc_name: str) -> Vpc:

        if not vpc_name:
            vpc_name = f"{session.profile_name}-{env_name}"

        try:
            vpc = self.vpc_provider.get_vpc(app_name, env_name, vpc_name)
        except VpcNotFoundForNameException:
            vpc = self.vpc_provider.get_vpc(app_name, env_name, session.profile_name)

        if not vpc:
            raise VpcNotFoundForNameException

        return vpc

    def _match_subnet_id_order_to_cloudformation_exports(
        self, environment_name: str, vpc: Vpc
    ) -> Vpc:
        """
        Addresses an issue identified in DBTP-1524 'If the order of the subnets
        in the environment manifest has changed, copilot env deploy tries to do
        destructive changes.'.

        Takes a Vpc object which has a private and public subnets attribute and
        sorts them to match the order within cfn exports.
        """

        exports = self.cloudformation_provider.get_cloudformation_exports_for_environment(
            environment_name
        )

        public_subnet_exports = []
        private_subnet_exports = []

        for export in exports:
            if export["Name"].endswith("-PublicSubnets"):
                public_subnet_exports = export["Value"].split(",")
            elif export["Name"].endswith("-PrivateSubnets"):
                private_subnet_exports = export["Value"].split(",")

        # If the elements match, regardless of order, use the list from the CloudFormation exports
        if set(vpc.public_subnets) == set(public_subnet_exports):
            vpc.public_subnets = public_subnet_exports
        if set(vpc.private_subnets) == set(private_subnet_exports):
            vpc.private_subnets = private_subnet_exports

        return vpc


class CopilotTemplating:
    def __init__(
        self,
        file_provider: FileProvider = FileProvider(),
        io: ClickIOProvider = ClickIOProvider(),
        # TODO: DBTP-1958: file_provider can be moved up a layer.  File writing can be the responsibility of CopilotEnvironment generate
        # Or we align with PlatformTerraformManifestGenerator and rename from Templating to reflect the file writing responsibility
    ):
        self.file_provider = file_provider
        self.templates = setup_templates()
        self.io = io

    def generate_copilot_environment_manifest(
        self, environment_name: str, vpc: Vpc, cert_arn: str
    ) -> str:
        env_template = self.templates.get_template("env/manifest.yml")

        return env_template.render(
            {
                "name": environment_name,
                "vpc_id": vpc.id,
                "pub_subnet_ids": vpc.public_subnets,
                "priv_subnet_ids": vpc.private_subnets,
                "certificate_arn": cert_arn,
            }
        )

    def write_environment_manifest(self, environment_name: str, manifest_contents: str) -> str:

        return self.file_provider.mkfile(
            ".",
            f"copilot/environments/{environment_name}/manifest.yml",
            manifest_contents,
            overwrite=True,
        )

    def generate_cross_account_s3_policies(self, environments: dict, extensions):
        resource_blocks = defaultdict(list)

        for ext_name, ext_data in extensions.items():
            for env_name, env_data in ext_data.get("environments", {}).items():
                if "cross_environment_service_access" in env_data:
                    bucket = env_data.get("bucket_name")
                    x_env_data = env_data["cross_environment_service_access"]
                    for access_name, access_data in x_env_data.items():
                        service = access_data.get("service")
                        read = access_data.get("read", False)
                        write = access_data.get("write", False)
                        if read or write:
                            resource_blocks[service].append(
                                {
                                    "bucket_name": bucket,
                                    "app_prefix": camel_case(f"{service}-{bucket}-{access_name}"),
                                    "bucket_env": env_name,
                                    "access_env": access_data.get("environment"),
                                    "bucket_account": environments.get(env_name, {})
                                    .get("accounts", {})
                                    .get("deploy", {})
                                    .get("id"),
                                    "read": read,
                                    "write": write,
                                }
                            )

        if not resource_blocks:
            self.io.info("\n>>> No cross-environment S3 policies to create.\n")
            return

        for service in sorted(resource_blocks.keys()):
            resources = resource_blocks[service]
            self.io.info(f"\n>>> Creating S3 cross account policies for {service}.\n")
            template = self.templates.get_template(S3_CROSS_ACCOUNT_POLICY)
            file_content = template.render({"resources": resources})
            output_dir = Path(".").absolute()
            file_path = f"copilot/{service}/addons/s3-cross-account-policy.yml"

            self.file_provider.mkfile(output_dir, file_path, file_content, True)
            self.io.info(f"File {file_path} created")
