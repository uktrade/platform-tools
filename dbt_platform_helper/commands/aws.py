# from configparser import ConfigParser
import configparser
import io
import time
import webbrowser
from pathlib import Path
from typing import Dict
from typing import List

import boto3
import click

from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)

REGION = "eu-west-2"
start_url = "https://uktrade.awsapps.com/start"
sso_client = boto3.client("sso", region_name=REGION)
sso_oidc_client = boto3.client("sso-oidc", region_name=REGION)


def create_oidc_application(oidc_client):
    print("Creating temporary AWS SSO OIDC application")
    client = oidc_client.register_client(
        clientName="OIDC-app",
        clientType="public",
    )
    client_id = client.get("clientId")
    client_secret = client.get("clientSecret")
    return client_id, client_secret


def initiate_device_code_flow(client, oidc_application, url):
    print("Initiating device code flow")
    auth = client.start_device_authorization(
        clientId=oidc_application[0],
        clientSecret=oidc_application[1],
        startUrl=url,
    )

    url = auth.get("verificationUriComplete")
    device_code = auth.get("deviceCode")
    expires_in = auth.get("expiresIn")
    return url, device_code, expires_in


def open_browser_for_auth(url, client_id, client_secret, device_code):
    access_token = None
    webbrowser.open(url, new=2)
    for i in range(10):
        time.sleep(1)
        try:
            access_token = get_access_token(client_id, client_secret, device_code)
        except sso_oidc_client.exceptions.InvalidGrantException as e:
            click.secho(e.response, fg="red")
        if access_token:
            break
    return access_token


def get_access_token(client_id, client_secret, device_code):
    token_response = sso_oidc_client.create_token(
        clientId=client_id,
        clientSecret=client_secret,
        grantType="urn:ietf:params:oauth:grant-type:device_code",
        deviceCode=device_code,
    )
    return token_response


def get_aws_accounts(client, token) -> List[Dict[str, str]]:
    aws_accounts_response = client.list_accounts(accessToken=token)
    account_list = aws_accounts_response.get("accountList", [])
    if not account_list:
        raise RuntimeError("Unable to retrieve AWS SSO account list\n")
    return account_list


def create_config_contents(accounts, config):
    for account in accounts:
        account_name = account["accountName"]
        account_id = account["accountId"]
        role_name = "AdministratorAccess"

        # fmt: off
        profile_name = f"profile {account_name.lower().replace(' ', '-')}"
        config[profile_name] = {
            "sso_start_url": "https://uktrade.awsapps.com/start",
            "sso_region": "eu-west-2",
            "sso_account_id": account_id,
            "sso_role_name": role_name,
            "region": "eu-west-2",
        }
    config_str = io.StringIO()
    config.write(config_str)
    config_string_value = config_str.getvalue()
    return config_string_value


@click.group(chain=True, cls=ClickDocOptGroup)
def aws():
    """AWS commands."""
    check_platform_helper_version_needs_update()


@aws.command()
def configure():
    # Todo: doc comment
    # sso_client = session.client("sso")
    client_id, client_secret = create_oidc_application(sso_oidc_client)
    url, device_code, expires_in = initiate_device_code_flow(
        sso_oidc_client, create_oidc_application(sso_oidc_client), start_url
    )

    click.secho(client_id, fg="yellow")
    click.secho(client_secret, fg="blue")
    click.secho(url, fg="cyan")
    click.secho(device_code, fg="red")
    click.secho(expires_in, fg="yellow")

    # token_response = get_access_token(client_id, client_secret, device_code)
    # sso_token = token_response.get("token")
    token_response = open_browser_for_auth(url, client_id, client_secret, device_code)

    click.secho(token_response, fg="green")
    config_parser = configparser.ConfigParser()
    directory = "."

    accounts = get_aws_accounts(sso_client, token_response)
    config_string_value = create_config_contents(accounts, config_parser)
    mkfile(Path(directory), "aws_test_config.ini", config_string_value, overwrite=True)

    with open("aws_test_config.ini", "r") as file:
        file_contents = file.read()

        click.secho("Available AWS account profiles and configuration:", fg="green")
        click.secho(file_contents, fg="yellow")
