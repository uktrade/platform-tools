from collections import defaultdict
from pathlib import Path

import boto3
import click

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.aws import AWSException
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.load_balancers import find_https_listener
from dbt_platform_helper.providers.vpc import VpcProvider
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.template import S3_CROSS_ACCOUNT_POLICY
from dbt_platform_helper.utils.template import camel_case
from dbt_platform_helper.utils.template import setup_templates


# TODO - prob some error message here... e.g. "VPC: {vpc_name} not found in account, check your platform-config.yaml and aws-profile configuration"
class VPCNotFoundError(PlatformException):
    pass


# TODO - move helper functions into suitable provider classes
# VPC Provider method
def get_subnet_ids(session, vpc_id, environment_name):
    subnets = session.client("ec2").describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["Subnets"]

    if not subnets:
        click.secho(f"No subnets found for VPC with id: {vpc_id}.", fg="red")
        raise click.Abort

    public_tag = {"Key": "subnet_type", "Value": "public"}
    public_subnets = [subnet["SubnetId"] for subnet in subnets if public_tag in subnet["Tags"]]
    private_tag = {"Key": "subnet_type", "Value": "private"}
    private_subnets = [subnet["SubnetId"] for subnet in subnets if private_tag in subnet["Tags"]]

    # This call and the method declaration can be removed when we stop using AWS Copilot to deploy the services
    public_subnets, private_subnets = _match_subnet_id_order_to_cloudformation_exports(
        session,
        environment_name,
        public_subnets,
        private_subnets,
    )

    return public_subnets, private_subnets


def _match_subnet_id_order_to_cloudformation_exports(
    session, environment_name, public_subnets, private_subnets
):
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


def get_cert_arn(session, application, env_name):
    try:
        arn = find_https_certificate(session, application, env_name)
    except:
        click.secho(
            f"No certificate found with domain name matching environment {env_name}.", fg="red"
        )
        raise click.Abort

    return arn


def find_https_certificate(session: boto3.Session, app: str, env: str) -> str:
    listener_arn = find_https_listener(session, app, env)
    cert_client = session.client("elbv2")
    certificates = cert_client.describe_listener_certificates(ListenerArn=listener_arn)[
        "Certificates"
    ]

    try:
        certificate_arn = next(c["CertificateArn"] for c in certificates if c["IsDefault"])
    except StopIteration:
        raise CertificateNotFoundException()

    return certificate_arn


class CertificateNotFoundException(PlatformException):
    pass


class CopilotEnvironment:
    def __init__(self, config_provider, vpc_provider=None):
        self.config_provider = config_provider
        self.vpc_provider = vpc_provider

    def generate(self, environment_name):

        config = self.config_provider.load_and_validate_platform_config()
        enriched_config = self.config_provider.apply_environment_defaults(config)

        env_config = enriched_config["environments"][environment_name]
        profile_for_environment = env_config.get("accounts", {}).get("deploy", {}).get("name")
        click.secho(f"Using {profile_for_environment} for this AWS session")

        # Interrim setup stuff TBA/TODO determine where this lives
        session = get_aws_session_or_abort(profile_for_environment)
        vpc_provider = self.vpc_provider(session)  # TODO
        copilot_templating = CopilotTemplating(vpc_provider, FileProvider, FileProvider().mkfile())

        copilot_templating.generate_copilot_environment_manifests(
            environment_name, enriched_config["application"], env_config, session, vpc_provider
        )


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

    def generate_copilot_environment_manifests(
        self, environment_name, application_name, env_config, session
    ):
        env_template = setup_templates().get_template("env/manifest.yml")

        # Get template variables
        vpc_id = self._get_environment_vpc_id(
            session, environment_name, env_config.get("vpc", None)
        )
        pub_subnet_ids, priv_subnet_ids = get_subnet_ids(session, vpc_id, environment_name)
        cert_arn = get_cert_arn(session, application_name, environment_name)

        return env_template.render(
            {
                "name": environment_name,
                "vpc_id": vpc_id,
                "pub_subnet_ids": pub_subnet_ids,
                "priv_subnet_ids": priv_subnet_ids,
                "certificate_arn": cert_arn,
            }
        )
        # click.echo(self._write_template(environment_name, manifest_contents))

    def _write_template(self, environment_name: str, manifest_contents: str):

        return click.echo(
            self.file_provider.mkfile(
                ".",
                f"copilot/environments/{environment_name}/manifest.yml",
                manifest_contents,
                overwrite=True,
            )
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
    def _get_environment_vpc_id(self, session, env_name, vpc_name):

        if not vpc_name:
            vpc_name = f"{session.profile_name}-{env_name}"

        try:
            vpc_id = self.vpc_provider.get_vpc_id_by_name(vpc_name)
        except AWSException:
            vpc_id = self.vpc_provider.get_vpc_id_by_name(session.profile_name)

        if not vpc_id:
            raise VPCNotFoundError

        return vpc_id
