#!/usr/bin/env python
import click

from dbt_platform_helper.commands.copilot import make_addons
from dbt_platform_helper.commands.pipeline import generate as pipeline_generate
from dbt_platform_helper.utils.click import ClickDocOptCommand
from dbt_platform_helper.utils.versioning import check_platform_helper_version_mismatch
from dbt_platform_helper.utils.versioning import generate_platform_helper_version_file


@click.command(cls=ClickDocOptCommand)
@click.pass_context
def generate(ctx: click.Context):
    """
    Generate deployment pipeline configuration files and generate addons
    CloudFormation template files for each environment.

    Wraps pipeline generate and make-addons.
    """

    generate_platform_helper_version_file()
    check_platform_helper_version_mismatch()
    ctx.invoke(pipeline_generate)
    ctx.invoke(make_addons)
