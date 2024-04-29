from pathlib import Path

import click

from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)


@click.group(chain=True, cls=ClickDocOptGroup)
def aws():
    """AWS commands."""
    check_platform_helper_version_needs_update()


@aws.command()
def configure():
    # Todo: doc comment
    get_aws_session_or_abort()

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
