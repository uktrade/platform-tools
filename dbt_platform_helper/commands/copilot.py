#!/usr/bin/env python

import click

from dbt_platform_helper.domain.copilot import Copilot
from dbt_platform_helper.domain.copilot_environment import CopilotTemplating
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.kms import KMSProvider
from dbt_platform_helper.providers.parameter_store import ParameterStore
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup

# TODOs
# Inject session into class, remove get_aws_session_or_abort from domain. Patching needs to be moved to dbt_platform_helper.commands.copilot instead of dbt_platform_helper.domain.copilot.
# Validate unit tests are running - add additional patching if needed.
# Check test coverage via codecov, shouldn't have gone down.


@click.group(chain=True, cls=ClickDocOptGroup)
def copilot():
    PlatformHelperVersioning().check_if_needs_update()


@copilot.command()
def make_addons():
    """Generate addons CloudFormation for each environment."""
    try:
        session = get_aws_session_or_abort()
        parameter_provider = ParameterStore(session.client("ssm"))
        config_provider = ConfigProvider(ConfigValidator())
        kms_provider = KMSProvider(session.client("kms"))
        Copilot(
            config_provider=config_provider,
            parameter_provider=parameter_provider,
            file_provider=FileProvider(),
            copilot_templating=CopilotTemplating(),
            kms_provider=kms_provider,
            session=session,
        ).make_addons()
    except Exception as err:
        ClickIOProvider().abort_with_error(str(err))
