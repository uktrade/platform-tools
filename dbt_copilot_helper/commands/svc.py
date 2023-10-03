#!/usr/bin/env python

import subprocess

import click

from dbt_copilot_helper.utils.click import ClickDocOptGroup
from dbt_copilot_helper.utils.versioning import (
    check_copilot_helper_version_needs_update,
)


@click.group(chain=True, cls=ClickDocOptGroup)
def svc():
    """AWS Copilot svc actions with DBT extras."""
    check_copilot_helper_version_needs_update()


@svc.command()
@click.option("--env", type=str, required=True)
@click.option("--name", type=str, required=True)
@click.option("--image-tag", type=str, required=False, show_default=True, default="latest")
def deploy(env, name, image_tag):
    """Deploy image tag to a service, default to image tagged latest."""

    # Todo: If --image-tag is unset or latest, figure out the image tag from AWS ECR or blow up

    command = f"IMAGE_TAG={image_tag} copilot svc deploy --env {env} --name {name}"
    print("Running: ", command)
    subprocess.call(
        command,
        shell=True,
    )
