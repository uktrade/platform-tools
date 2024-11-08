import boto3
import click
from schema import SchemaError

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.domain.maintenance_page import MaintenancePageProvider
from dbt_platform_helper.providers.load_balancers import find_https_listener
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.template import setup_templates
from dbt_platform_helper.utils.validation import load_and_validate_platform_config
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)

AVAILABLE_TEMPLATES = ["default", "migration", "dmas-migration"]


@click.group(cls=ClickDocOptGroup)
def environment():
    """Commands affecting environments."""
    check_platform_helper_version_needs_update()


@environment.command()
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
@click.option("--svc", type=str, required=True, multiple=True, default=["web"])
@click.option(
    "--template",
    type=click.Choice(AVAILABLE_TEMPLATES),
    default="default",
    help="The maintenance page you wish to put up.",
)
@click.option("--vpc", type=str)
def offline(app, env, svc, template, vpc):
    """Take load-balanced web services offline with a maintenance page."""
    maintenance_page = MaintenancePageProvider()
    maintenance_page.activate(app, env, svc, template, vpc)


@environment.command()
@click.option("--app", type=str, required=True)
@click.option("--env", type=str, required=True)
def online(app, env):
    """Remove a maintenance page from an environment."""
    maintenance_page = MaintenancePageProvider()
    maintenance_page.deactivate(app, env)


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


def get_subnet_ids(session, vpc_id):
    subnets = session.client("ec2").describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["Subnets"]

    if not subnets:
        click.secho(f"No subnets found for VPC with id: {vpc_id}.", fg="red")
        raise click.Abort

    public_tag = {"Key": "subnet_type", "Value": "public"}
    public = [subnet["SubnetId"] for subnet in subnets if public_tag in subnet["Tags"]]
    private_tag = {"Key": "subnet_type", "Value": "private"}
    private = [subnet["SubnetId"] for subnet in subnets if private_tag in subnet["Tags"]]

    return public, private


def get_cert_arn(session, application, env_name):
    try:
        arn = find_https_certificate(session, application, env_name)
    except:
        click.secho(
            f"No certificate found with domain name matching environment {env_name}.", fg="red"
        )
        raise click.Abort

    return arn


@environment.command()
@click.option("--vpc-name", hidden=True)
@click.option("--name", "-n", required=True)
def generate(name, vpc_name):
    if vpc_name:
        click.secho(
            f"This option is deprecated. Please add the VPC name for your envs to {PLATFORM_CONFIG_FILE}",
            fg="red",
        )
        raise click.Abort

    try:
        conf = load_and_validate_platform_config()
    except SchemaError as ex:
        click.secho(f"Invalid `{PLATFORM_CONFIG_FILE}` file: {str(ex)}", fg="red")
        raise click.Abort

    env_config = apply_environment_defaults(conf)["environments"][name]
    profile_for_environment = env_config.get("accounts", {}).get("deploy", {}).get("name")
    click.secho(f"Using {profile_for_environment} for this AWS session")
    session = get_aws_session_or_abort(profile_for_environment)

    _generate_copilot_environment_manifests(name, conf["application"], env_config, session)


@environment.command(help="Generate terraform manifest for the specified environment.")
@click.option(
    "--name", "-n", required=True, help="The name of the environment to generate a manifest for."
)
@click.option(
    "--terraform-platform-modules-version",
    help=f"Override the default version of terraform-platform-modules. (Default version is '{DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION}').",
)
def generate_terraform(name, terraform_platform_modules_version):
    conf = load_and_validate_platform_config()

    env_config = apply_environment_defaults(conf)["environments"][name]
    _generate_terraform_environment_manifests(
        conf["application"], name, env_config, terraform_platform_modules_version
    )


def _generate_copilot_environment_manifests(name, application, env_config, session):
    env_template = setup_templates().get_template("env/manifest.yml")
    vpc_name = env_config.get("vpc", None)
    vpc_id = get_vpc_id(session, name, vpc_name)
    pub_subnet_ids, priv_subnet_ids = get_subnet_ids(session, vpc_id)
    cert_arn = get_cert_arn(session, application, name)
    contents = env_template.render(
        {
            "name": name,
            "vpc_id": vpc_id,
            "pub_subnet_ids": pub_subnet_ids,
            "priv_subnet_ids": priv_subnet_ids,
            "certificate_arn": cert_arn,
        }
    )
    click.echo(mkfile(".", f"copilot/environments/{name}/manifest.yml", contents, overwrite=True))


def _generate_terraform_environment_manifests(
    application, env, env_config, cli_terraform_platform_modules_version
):
    env_template = setup_templates().get_template("environments/main.tf")

    terraform_platform_modules_version = _determine_terraform_platform_modules_version(
        env_config, cli_terraform_platform_modules_version
    )

    contents = env_template.render(
        {
            "application": application,
            "environment": env,
            "config": env_config,
            "terraform_platform_modules_version": terraform_platform_modules_version,
        }
    )

    click.echo(mkfile(".", f"terraform/environments/{env}/main.tf", contents, overwrite=True))


def _determine_terraform_platform_modules_version(env_conf, cli_terraform_platform_modules_version):
    cli_terraform_platform_modules_version = cli_terraform_platform_modules_version
    env_conf_terraform_platform_modules_version = env_conf.get("versions", {}).get(
        "terraform-platform-modules"
    )
    version_preference_order = [
        cli_terraform_platform_modules_version,
        env_conf_terraform_platform_modules_version,
        DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION,
    ]
    return [version for version in version_preference_order if version][0]


def find_https_certificate(session: boto3.Session, app: str, env: str) -> str:
    listener_arn = find_https_listener(session, app, env)
    cert_client = session.client("elbv2")
    certificates = cert_client.describe_listener_certificates(ListenerArn=listener_arn)[
        "Certificates"
    ]

    try:
        certificate_arn = next(c["CertificateArn"] for c in certificates if c["IsDefault"])
    except StopIteration:
        raise CertificateNotFoundError()

    return certificate_arn


class CertificateNotFoundError(Exception):
    pass
