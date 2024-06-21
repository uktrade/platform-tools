import os
import webbrowser
from pathlib import Path
from typing import Dict

import boto3
import botocore
import click
from prettytable import PrettyTable

from dbt_platform_helper.exceptions import IncompatibleMajorVersion
from dbt_platform_helper.exceptions import ValidationException
from dbt_platform_helper.utils import versioning
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.files import config_file_check

yes = "\033[92m✔\033[0m"
no = "\033[91m✖\033[0m"
maybe = "\033[93m?\033[0m"

RECOMMENDATIONS = {
    "dbt-platform-helper-upgrade": (
        "Upgrade dbt-platform-helper to version {version} `pip install "
        "--upgrade dbt-platform-helper=={version}`."
    ),
    "dbt-platform-helper-upgrade-note": (
        "Post upgrade, run `platform-helper copilot make-addons` to " "update your addon templates."
    ),
    "generic-tool-upgrade": "Upgrade {tool} to version {version}.",
}

SSO_START_URL = "https://uktrade.awsapps.com/start"

AWS_CONFIG = """
#
# uktrade
#

[sso-session uktrade]
sso_start_url = https://uktrade.awsapps.com/start#/
sso_region = eu-west-2
sso_registration_scopes = sso:account:access

"""


@click.group(cls=ClickDocOptGroup)
def config():
    """Perform actions on configuration files."""


@config.command()
def validate():
    """Validate deployment or application configuration."""
    ran_checks = False
    if Path("copilot").exists():
        click.secho("\nDetected a deployment repository", fg="blue")
        deployment()
        ran_checks = True

    if not ran_checks:
        click.secho("Could not find a deployment repository, no checks to run.", fg="red")
        exit(1)


def deployment():
    click.secho()

    compatible = True

    tool_versions()
    click.secho("Checking addons templates versions...", fg="blue")

    app_version, app_released_version = versioning.get_app_versions()
    addons_templates_table = PrettyTable()
    addons_templates_table.field_names = [
        "Addons Template File",
        "Generated with",
        "Compatible with local?",
        "Compatible with latest?",
    ]
    addons_templates_table.align["Addons Template File"] = "l"

    addons_templates = list(Path("./copilot").glob("**/addons/*"))
    # Sort by template file path
    addons_templates.sort(key=lambda e: str(e))
    # Bring environment addons to the top
    addons_templates.sort(key=lambda e: "environments/" not in str(e))

    recommendations = {}

    config_file_check()

    for template_file in addons_templates:
        generated_with_version = maybe
        local_compatible_symbol = yes
        latest_compatible_symbol = yes

        try:
            generated_with_version = versioning.get_template_generated_with_version(
                str(template_file.resolve())
            )
            versioning.validate_template_version(app_version, str(template_file.resolve()))
        except IncompatibleMajorVersion:
            local_compatible_symbol = no
            compatible = False
            recommendations["dbt-platform-helper-upgrade"] = RECOMMENDATIONS[
                "dbt-platform-helper-upgrade"
            ].format(version=versioning.string_version(app_released_version))
            recommendations["dbt-platform-helper-upgrade-note"] = RECOMMENDATIONS[
                "dbt-platform-helper-upgrade-note"
            ]
        except ValidationException:
            local_compatible_symbol = maybe
            compatible = False
            recommendations["dbt-platform-helper-upgrade"] = RECOMMENDATIONS[
                "dbt-platform-helper-upgrade"
            ].format(version=versioning.string_version(app_released_version))
            recommendations["dbt-platform-helper-upgrade-note"] = RECOMMENDATIONS[
                "dbt-platform-helper-upgrade-note"
            ]

        try:
            generated_with_version = versioning.get_template_generated_with_version(
                str(template_file.resolve())
            )
            versioning.validate_template_version(app_released_version, str(template_file.resolve()))
        except IncompatibleMajorVersion:
            latest_compatible_symbol = no
            compatible = False
        except ValidationException:
            latest_compatible_symbol = maybe
            compatible = False

        addons_templates_table.add_row(
            [
                template_file.relative_to("."),
                (
                    maybe
                    if latest_compatible_symbol is maybe
                    else versioning.string_version(generated_with_version)
                ),
                local_compatible_symbol,
                latest_compatible_symbol,
            ]
        )

    click.secho(addons_templates_table)
    render_recommendations(recommendations)

    exit(0 if compatible else 1)


def tool_versions():
    click.secho("Checking tooling versions...", fg="blue")
    recommendations = {}

    copilot_version, copilot_released_version = versioning.get_copilot_versions()
    if copilot_version is None:
        recommendations["install-copilot"] = (
            "Install AWS Copilot https://aws.github.io/copilot-cli/"
        )

    aws_version, aws_released_version = versioning.get_aws_versions()
    if aws_version is None:
        recommendations["install-aws"] = "Install AWS CLI https://aws.amazon.com/cli/"

    app_version, app_released_version = versioning.get_app_versions()

    tool_versions_table = PrettyTable()
    tool_versions_table.field_names = [
        "Tool",
        "Local version",
        "Released version",
        "Running latest?",
    ]
    tool_versions_table.align["Tool"] = "l"

    tool_versions_table.add_row(
        [
            "aws",
            versioning.string_version(aws_version),
            versioning.string_version(aws_released_version),
            no if aws_version != aws_released_version else yes,
        ]
    )
    tool_versions_table.add_row(
        [
            "copilot",
            versioning.string_version(copilot_version),
            versioning.string_version(copilot_released_version),
            no if copilot_version != copilot_released_version else yes,
        ]
    )
    tool_versions_table.add_row(
        [
            "dbt-platform-helper",
            versioning.string_version(app_version),
            versioning.string_version(app_released_version),
            no if app_version != app_released_version else yes,
        ]
    )

    click.secho(tool_versions_table)

    if aws_version != aws_released_version and "install-aws" not in recommendations:
        recommendations["aws-upgrade"] = RECOMMENDATIONS["generic-tool-upgrade"].format(
            tool="AWS CLI",
            version=versioning.string_version(aws_released_version),
        )

    if copilot_version != copilot_released_version and "install-copilot" not in recommendations:
        recommendations["copilot-upgrade"] = RECOMMENDATIONS["generic-tool-upgrade"].format(
            tool="AWS Copilot",
            version=versioning.string_version(copilot_released_version),
        )

    if app_version != app_released_version:
        recommendations["dbt-platform-helper-upgrade"] = RECOMMENDATIONS[
            "dbt-platform-helper-upgrade"
        ].format(version=versioning.string_version(app_released_version))
        recommendations["dbt-platform-helper-upgrade-note"] = RECOMMENDATIONS[
            "dbt-platform-helper-upgrade-note"
        ]

    render_recommendations(recommendations)


def render_recommendations(recommendations: Dict[str, str]):
    if recommendations:
        click.secho("\nRecommendations:\n", bold=True)

        for name, recommendation in recommendations.items():
            if name.endswith("-note"):
                continue
            click.secho(f"  - {recommendation}")
            if recommendations.get(f"{name}-note", False):
                click.secho(f"    {recommendations.get(f'{name}-note')}")

        click.secho()


@config.command()
@click.option("--file-path", "-fp", default="~/.aws/config")
def aws(file_path):
    """
    Writes a local config file containing all the AWS profiles to which the
    logged in user has access.

    If no `--file-path` is specified, defaults to `~/.aws/config`.
    """
    sso_oidc_client = boto3.client("sso-oidc", region_name="eu-west-2")
    sso_client = boto3.client("sso", region_name="eu-west-2")
    oidc_app = create_oidc_application(sso_oidc_client)
    verification_url, device_code = get_device_code(sso_oidc_client, oidc_app, SSO_START_URL)

    if click.confirm(
        "You are about to be redirected to a verification page. You will need to complete sign-in before returning to the command line. Do you want to continue?",
        abort=True,
    ):
        webbrowser.open(verification_url)

    if click.confirm("Have you completed the sign-in process in your browser?", abort=True):
        access_token = get_access_token(device_code, sso_oidc_client, oidc_app)

    aws_config_path = os.path.expanduser(file_path)

    if click.confirm(
        f"This command is destructive and will overwrite file contents at {file_path}. Are you sure you want to continue?",
        abort=True,
    ):
        with open(aws_config_path, "w") as config_file:
            config_file.write(AWS_CONFIG)

            for account in retrieve_aws_accounts(sso_client, access_token):
                config_file.write(f"[profile {account['accountName']}]\n")
                config_file.write("sso_session = uktrade\n")
                config_file.write(f"sso_account_id = {account['accountId']}\n")
                config_file.write("sso_role_name = AdministratorAccess\n")
                config_file.write("region = eu-west-2\n")
                config_file.write("output = json\n")
                config_file.write("\n")


def create_oidc_application(sso_oidc_client):
    print("Creating temporary AWS SSO OIDC application")
    client = sso_oidc_client.register_client(
        clientName="platform-helper",
        clientType="public",
    )
    client_id = client.get("clientId")
    client_secret = client.get("clientSecret")

    return client_id, client_secret


def get_device_code(sso_oidc_client, oidc_application, start_url):
    print("Initiating device code flow")
    authz = sso_oidc_client.start_device_authorization(
        clientId=oidc_application[0],
        clientSecret=oidc_application[1],
        startUrl=start_url,
    )
    url = authz.get("verificationUriComplete")
    deviceCode = authz.get("deviceCode")

    return url, deviceCode


def retrieve_aws_accounts(sso_client, aws_sso_token):
    aws_accounts_response = sso_client.list_accounts(
        accessToken=aws_sso_token,
        maxResults=100,
    )
    if len(aws_accounts_response.get("accountList", [])) == 0:
        raise RuntimeError("Unable to retrieve AWS SSO account list\n")
    return aws_accounts_response.get("accountList")


def get_access_token(device_code, sso_oidc_client, oidc_app):
    try:
        token_response = sso_oidc_client.create_token(
            clientId=oidc_app[0],
            clientSecret=oidc_app[1],
            grantType="urn:ietf:params:oauth:grant-type:device_code",
            deviceCode=device_code,
        )

        return token_response.get("accessToken")

    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] != "AuthorizationPendingException":
            raise e
