from pathlib import Path
from typing import Dict
from typing import List

import click

from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)


def get_aws_accounts(client, creds) -> List[Dict[str, str]]:
    aws_accounts_response = client.list_accounts(accessToken=creds.get("token"))
    if len(aws_accounts_response.get("accountList", [])) == 0:
        raise RuntimeError("Unable to retrieve AWS SSO account list\n")
    return aws_accounts_response.get("accountList")


@click.group(chain=True, cls=ClickDocOptGroup)
def aws():
    """AWS commands."""
    check_platform_helper_version_needs_update()


@aws.command()
def configure():
    # Todo: doc comment

    session = get_aws_session_or_abort()
    sso_client = session.client("sso")
    credentials = session.get_credentials()

    get_aws_accounts(sso_client, credentials)

    profile_configurations = """[default]
region=eu-west-2
sso_start_url=https://uktrade.awsapps.com/start
sso_region=eu-west-2
sso_account_id = 123456789
sso_role_name = AdministratorAccess

[profile test-account]
sso_start_url=https://uktrade.awsapps.com/start
sso_region=eu-west-2
sso_account_id = 123456789
sso_role_name = AdministratorAccess
region=eu-west-2
"""

    Path("aws_config").write_text(profile_configurations)
