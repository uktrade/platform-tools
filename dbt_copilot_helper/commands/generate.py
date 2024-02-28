#!/usr/bin/env python
import click

from dbt_copilot_helper.commands.copilot import make_addons
from dbt_copilot_helper.commands.pipeline import generate as pipeline_generate
from dbt_copilot_helper.utils.click import ClickDocOptGroup


@click.group(chain=True, cls=ClickDocOptGroup)
def generate():
    pipeline_generate()
    make_addons()
