#!/usr/bin/env python
import click

from dbt_platform_helper.commands.copilot import make_addons
from dbt_platform_helper.commands.pipeline import generate as pipeline_generate
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.utils.click import ClickDocOptCommand


@click.command(cls=ClickDocOptCommand)
@click.pass_context
def generate(ctx: click.Context):
    """
    Generate deployment pipeline configuration files and generate addons
    CloudFormation template files for each environment.

    Wraps pipeline generate and make-addons.
    """
    PlatformHelperVersioning().check_platform_helper_version_mismatch()
    ctx.invoke(pipeline_generate)
    ctx.invoke(make_addons)
