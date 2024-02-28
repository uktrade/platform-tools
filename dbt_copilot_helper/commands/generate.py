#!/usr/bin/env python
import click

from dbt_copilot_helper.commands.copilot import make_addons
from dbt_copilot_helper.commands.pipeline import generate as pipeline_generate
from dbt_copilot_helper.utils.click import ClickDocOptCommand


@click.command(cls=ClickDocOptCommand)
@click.pass_context
def generate(ctx: click.Context):
    """
    Given a pipelines.yml file, generate environment and service deployment
    pipelines and generate addons CloudFormation for each environment.

    Wraps pipeline generate and make-addons.
    """

    ctx.invoke(pipeline_generate)
    ctx.invoke(make_addons)
