#!/usr/bin/env python

from os import makedirs
from pathlib import Path

import click

from dbt_copilot_helper.utils.click import ClickDocOptGroup
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

    base_path = Path(directory)
    pipelines_environments_dir = base_path / "copilot/pipelines/my-app-environments"
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


# def deploy(env, name, image_tag):
#     """Deploy image tag to a service, defaults to image tagged latest."""
#
#     repository_name = validate_service_manifest_and_return_repository(name)
#
#     image_tags = get_all_tags_for_image(image_tag, repository_name)
#
#     if image_tag == "latest":
#         image_tag = get_commit_tag_for_latest_image(image_tags)
#
#     command = f"IMAGE_TAG={image_tag} copilot svc deploy --env {env} --name {name}"
#     click.echo(f"Running: {command}")
#     subprocess.call(
#         command,
#         shell=True,
#     )
