#!/usr/bin/env python
import click

from dbt_copilot_helper.commands.copilot import make_addons
from dbt_copilot_helper.commands.pipeline import generate as pipeline_generate


@click.command()
def generate():
    """
    Given a pipelines.yml file, generate environment and service deployment
    pipelines and generate addons CloudFormation for each environment.

    Wraps pipeline generate and make-addons.
    """
    pipeline_generate()
    make_addons()
