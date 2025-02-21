#!/usr/bin/env python

import click

from dbt_platform_helper.domain.copilot import Copilot
from dbt_platform_helper.domain.copilot_environment import CopilotTemplating
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.platform_helper_versioning import (
    PlatformHelperVersioning,
)
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)


# TODOs
# Figure out a pattern for copilot templating and the new copilot domain - probably a lot of overlap here that really belongs in the copilottemplating domain instead (atleast whatever is concerned with "templating")
# Check for E2E test coverage.


@click.group(chain=True, cls=ClickDocOptGroup)
def copilot():
    PlatformHelperVersioning().check_if_needs_update()


@copilot.command()
def make_addons():
    """Generate addons CloudFormation for each environment."""
    try:
        config_provider = ConfigProvider(ConfigValidator())
        Copilot(config_provider, FileProvider(), CopilotTemplating()).make_addons()
    except Exception as err:
        ClickIOProvider().abort_with_error(str(err))
