#!/usr/bin/env python

from os import makedirs
from pathlib import Path

import click

from dbt_copilot_helper.utils.click import ClickDocOptGroup
from dbt_copilot_helper.utils.files import load_and_validate_config
from dbt_copilot_helper.utils.files import mkfile
from dbt_copilot_helper.utils.template import setup_templates
from dbt_copilot_helper.utils.versioning import (
    check_copilot_helper_version_needs_update,
)


@click.group(chain=True, cls=ClickDocOptGroup)
def pipeline():
    """Pipeline commands."""
    check_copilot_helper_version_needs_update()


@pipeline.command()
@click.option("-d", "--directory", type=str, default=".")
def generate(directory="."):
    templates = setup_templates()
    config = load_and_validate_config("bootstrap.yml")

    base_path = Path(directory)
    pipelines_environments_dir = base_path / f"copilot/pipelines/{ config['app'] }-environments"
    overrides_dir = pipelines_environments_dir / "overrides"

    makedirs(overrides_dir)

    contents = templates.get_template("pipeline/buildspec.yml").render({})
    # click.echo(
    mkfile(base_path, pipelines_environments_dir / "buildspec.yml", contents)

    contents = templates.get_template("pipeline/manifest.yml").render({})
    # click.echo(
    mkfile(base_path, pipelines_environments_dir / "manifest.yml", contents)

    contents = templates.get_template("pipeline/overrides/cfn.patches.yml").render({})
    # click.echo(
    mkfile(base_path, pipelines_environments_dir / "overrides/cfn.patches.yml", contents)
