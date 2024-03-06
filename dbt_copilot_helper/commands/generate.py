#!/usr/bin/env python
import click

from dbt_copilot_helper.commands.copilot import make_addons
from dbt_copilot_helper.commands.pipeline import generate as pipeline_generate
from dbt_copilot_helper.utils.click import ClickDocOptCommand
from dbt_copilot_helper.utils.versioning import check_copilot_helper_version_mismatch


@click.command(cls=ClickDocOptCommand)
@click.pass_context
def generate(ctx: click.Context):
    """
    Generate deployment pipeline configuration files and generate addons
    CloudFormation template files for each environment.

    Wraps pipeline generate and make-addons.
    """
    check_copilot_helper_version_mismatch()
    ctx.invoke(pipeline_generate)
    ctx.invoke(make_addons)
