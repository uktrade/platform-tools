from collections import defaultdict
from pathlib import Path

import boto3
import click

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.load_balancers import find_https_listener
from dbt_platform_helper.providers.vpc import VpcNotFoundForNameException
from dbt_platform_helper.providers.vpc import VpcProvider
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.template import S3_CROSS_ACCOUNT_POLICY
from dbt_platform_helper.utils.template import camel_case
from dbt_platform_helper.utils.template import setup_templates


class CertificateNotFoundException(PlatformException):
    pass


# TODO move into CopilotTemplating.generate method...
def get_cert_arn(session: boto3.Session, app_name: str, env_name: str) -> str:
    try:
        arn = find_https_certificate(session, app_name, env_name)
    except:
        click.secho(
            f"No certificate found with domain name matching environment {env_name}.", fg="red"
        )
        raise click.Abort

    return arn


def find_https_certificate(session: boto3.Session, app_name: str, env_name: str) -> str:
    listener_arn = find_https_listener(session, app_name, env_name)
    cert_client = session.client("elbv2")
    certificates = cert_client.describe_listener_certificates(ListenerArn=listener_arn)[
        "Certificates"
    ]

    try:
        certificate_arn = next(c["CertificateArn"] for c in certificates if c["IsDefault"])
    except StopIteration:
        raise CertificateNotFoundException()

    return certificate_arn


class CopilotEnvironment:
    def __init__(self, config_provider, vpc_provider=None, copilot_templating=None):
        self.config_provider = config_provider
        self.vpc_provider = vpc_provider
        self.copilot_templating = copilot_templating or CopilotTemplating(
            vpc_provider=self.vpc_provider,
            file_provider=FileProvider,
            mkfile_fn=FileProvider.mkfile(),
        )

    def generate(self, environment_name):

        platform_config = self.config_provider.get_enriched_config()

        # TODO - potentially worth a look but this line throws an error if you provide an invalid env name...
        env_config = platform_config["environments"][environment_name]
        profile_for_environment = env_config.get("accounts", {}).get("deploy", {}).get("name")

        click.secho(
            f"Using {profile_for_environment} for this AWS session"
        )  # TODO - echo_fn and assert on result.

        session = get_aws_session_or_abort(
            profile_for_environment
        )  # TODO - session could likely fall away?

        copilot_environment_manifest = (
            self.copilot_templating.generate_copilot_environment_manifest(
                environment_name=environment_name,
                application_name=platform_config["application"],
                env_config=env_config,
                session=session,
            )
        )

        self.copilot_templating.write_template(environment_name, copilot_environment_manifest)


class CopilotTemplating:
    # TODO - remove mkfile_fn - inject provider instead
    def __init__(
        self,
        vpc_provider: VpcProvider = None,
        file_provider: FileProvider = None,
        mkfile_fn=FileProvider.mkfile,
    ):
        self.mkfile_fn = mkfile_fn
        self.vpc_provider = vpc_provider
        self.file_provider = file_provider

    def generate_copilot_environment_manifest(
        self, environment_name, application_name, env_config, session
    ):
        env_template = setup_templates().get_template("env/manifest.yml")

        vpc = self._get_environment_vpc(session, environment_name, env_config.get("vpc", None))

        print(f"VPC: {vpc.public_subnets}")

        return env_template.render(
            {
                "name": environment_name,
                "vpc_id": vpc.id,
                "pub_subnet_ids": vpc.public_subnets,
                "priv_subnet_ids": vpc.private_subnets,
                "certificate_arn": get_cert_arn(
                    session, application_name, environment_name
                ),  # TODO - likely lives in a loadbalancer provider,
            }
        )

    def write_template(self, environment_name: str, manifest_contents: str):

        return click.echo(
            self.file_provider.mkfile(
                ".",
                f"copilot/environments/{environment_name}/manifest.yml",
                manifest_contents,
                overwrite=True,
            )
        )

    def _match_subnet_id_order_to_cloudformation_exports(
        session, environment_name, public_subnets, private_subnets
    ):
        """Addresses an issue identified in DBTP-1524 'If the order of the
        subnets in the environment manifest has changed, copilot env deploy
        tries to do destructive changes.'."""
        public_subnet_exports = []
        private_subnet_exports = []

        for page in session.client("cloudformation").get_paginator("list_exports").paginate():
            for export in page["Exports"]:
                if f"-{environment_name}-" in export["Name"]:
                    if export["Name"].endswith("-PublicSubnets"):
                        public_subnet_exports = export["Value"].split(",")
                    if export["Name"].endswith("-PrivateSubnets"):
                        private_subnet_exports = export["Value"].split(",")

        # If the elements match, regardless of order, use the list from the CloudFormation exports
        if set(public_subnets) == set(public_subnet_exports):
            public_subnets = public_subnet_exports
        if set(private_subnets) == set(private_subnet_exports):
            private_subnets = private_subnet_exports

        return public_subnets, private_subnets

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
            click.echo("\n>>> No cross-environment S3 policies to create.\n")
            return

        templates = setup_templates()

        for service in sorted(resource_blocks.keys()):
            resources = resource_blocks[service]
            click.echo(f"\n>>> Creating S3 cross account policies for {service}.\n")
            template = templates.get_template(S3_CROSS_ACCOUNT_POLICY)
            file_content = template.render({"resources": resources})
            output_dir = Path(".").absolute()
            file_path = f"copilot/{service}/addons/s3-cross-account-policy.yml"

            self.mkfile_fn(output_dir, file_path, file_content, True)
            click.echo(f"File {file_path} created")

    # TODO: This functionality makes no sense... Why are we checking for a vpc in AWS under 3 different names (vpc_name, session.profile_name, {session.profile_name}-{env_name})
    # TODO - refactor this somehow
    # {session.profile_name}-{env_name} looks to work with the naming convention we use for our demodjango-deploy platform-config.yaml. Aghhh

    # TODO (with a clearer head after refactoring slightly) - Check with the team why we bother to check aws-profile names to find the VPC. Since these profile names can be named litterally anything it feels like a moot check to have.
    # If no one has a good reason for the check just remove it and fail fast if the VPC they provider in their platform config is invalid (and move on)
    def _get_environment_vpc(self, session, env_name, vpc_name):

        if not vpc_name:
            vpc_name = f"{session.profile_name}-{env_name}"

        try:
            vpc = self.vpc_provider.get_vpc(vpc_name)
        except VpcNotFoundForNameException:
            vpc = self.vpc_provider.get_vpc(session.profile_name)

        if not vpc:
            raise VpcNotFoundForNameException

        return vpc
