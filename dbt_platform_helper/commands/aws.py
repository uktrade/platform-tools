# from configparser import ConfigParser
import configparser
import io
from typing import Dict
from typing import List

import click

from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)


def get_aws_accounts(client, token) -> List[Dict[str, str]]:
    aws_accounts_response = client.list_accounts(accessToken=token)
    account_list = aws_accounts_response.get("accountList", [])
    if not account_list:
        raise RuntimeError("Unable to retrieve AWS SSO account list\n")
    return account_list


def get_aws_credentials(client, token, account_id, role_name="AdministratorAccess"):
    sts_creds = client.get_role_credentials(
        accessToken=token,
        roleName=role_name,
        accountId=account_id,
    )

    if "roleCredentials" not in sts_creds:
        raise RuntimeError("Unable to retrieve STS credentials")
    credentials = sts_creds.get("roleCredentials")
    if "accessKeyId" not in credentials:
        raise RuntimeError("Unable to retrieve STS credentials")

    return {
        "aws_access_key_id": credentials["accessKeyId"],
        "aws_secret_access_key": credentials["secretAccessKey"],
        "aws_session_token": credentials["sessionToken"],
        "expiration": credentials["expiration"],
        "role": role_name,
    }


@click.group(chain=True, cls=ClickDocOptGroup)
def aws():
    """AWS commands."""
    check_platform_helper_version_needs_update()


@aws.command()
def configure(directory="."):
    # Todo: doc comment

    session = get_aws_session_or_abort()
    sso_client = session.client("sso")
    session_credentials = session.get_credentials()
    config = configparser.ConfigParser()

    accounts = get_aws_accounts(sso_client, session_credentials.get("token"))
    for account in accounts:
        account_name = account["accountName"]
        account_id = account["accountId"]
        role_name = "AdministratorAccess"

        profile_name = f"profile {account_name.lower().replace(" ", " - ")}"
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

    # mkfile(Path(directory), "aws_test_config.ini", config)
    with open("./aws_test_config.ini", "w") as configfile:
        configfile.write(config_string_value)


#     profile_configurations = """[profile test-account-1]
# sso_start_url = https://uktrade.awsapps.com/start
# sso_region = eu-west-2
# sso_account_id = 123456789012
# sso_role_name = AdministratorAccess
# region = eu-west-2
#
# [profile test-account-2]
# sso_start_url = https://uktrade.awsapps.com/start
# sso_region = eu-west-2
# sso_account_id = 234567890123
# sso_role_name = AdministratorAccess
# region = eu-west-2
#
# """
#
#     Path("aws_config").write_text(profile_configurations)
