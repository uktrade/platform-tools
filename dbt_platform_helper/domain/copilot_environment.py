from collections import defaultdict
from pathlib import Path

import boto3
import click

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.load_balancers import find_https_listener
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.template import S3_CROSS_ACCOUNT_POLICY
from dbt_platform_helper.utils.template import camel_case
from dbt_platform_helper.utils.template import setup_templates


# TODO - move helper functions into suitable provider classes
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


def get_vpc_id(session, env_name, vpc_name=None):
    if not vpc_name:
        vpc_name = f"{session.profile_name}-{env_name}"

    filters = [{"Name": "tag:Name", "Values": [vpc_name]}]
    vpcs = session.client("ec2").describe_vpcs(Filters=filters)["Vpcs"]

    if not vpcs:
        filters[0]["Values"] = [session.profile_name]
        vpcs = session.client("ec2").describe_vpcs(Filters=filters)["Vpcs"]

    if not vpcs:
        click.secho(
            f"No VPC found with name {vpc_name} in AWS account {session.profile_name}.", fg="red"
        )
        raise click.Abort

    return vpcs[0]["VpcId"]


def _generate_copilot_environment_manifests(
    environment_name, application_name, env_config, session
):
    env_template = setup_templates().get_template("env/manifest.yml")
    vpc_name = env_config.get("vpc", None)
    vpc_id = get_vpc_id(session, environment_name, vpc_name)
    pub_subnet_ids, priv_subnet_ids = get_subnet_ids(session, vpc_id, environment_name)
    cert_arn = get_cert_arn(session, application_name, environment_name)
    contents = env_template.render(
        {
            "name": environment_name,
            "vpc_id": vpc_id,
            "pub_subnet_ids": pub_subnet_ids,
            "priv_subnet_ids": priv_subnet_ids,
            "certificate_arn": cert_arn,
        }
    )
    click.echo(
        mkfile(
            ".", f"copilot/environments/{environment_name}/manifest.yml", contents, overwrite=True
        )
    )


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
    def __init__(self, config_provider):
        self.config_provider = config_provider

    def generate(self, environment_name):
        config = self.config_provider.load_and_validate_platform_config()
        enriched_config = self.config_provider.apply_environment_defaults(config)

        env_config = enriched_config["environments"][environment_name]
        profile_for_environment = env_config.get("accounts", {}).get("deploy", {}).get("name")
        click.secho(f"Using {profile_for_environment} for this AWS session")
        session = get_aws_session_or_abort(profile_for_environment)

        _generate_copilot_environment_manifests(
            environment_name, enriched_config["application"], env_config, session
        )


class CopilotTemplating:
    def __init__(self, mkfile_fn=mkfile):
        self.mkfile_fn = mkfile_fn

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
