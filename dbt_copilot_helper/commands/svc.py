#!/usr/bin/env python

import re
import subprocess

import boto3
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
@click.option("--repository", type=str, required=True)
@click.option("--image-tag", type=str, required=False, show_default=True, default="latest")
def deploy(env, name, repository, image_tag):
    """Deploy image tag to a service, defaults to image tagged latest."""

    def get_all_tags_for_image(image_tag_needle):
        registry_id = boto3.client("sts").get_caller_identity()["Account"]
        ecr_client = boto3.client("ecr")
        try:
            response = ecr_client.describe_images(
                registryId=registry_id,
                repositoryName=repository,
                imageIds=[
                    {"imageTag": image_tag_needle},
                ],
            )
            return response["imageDetails"][0]["imageTags"]
        except ecr_client.exceptions.ImageNotFoundException:
            click.secho(
                f"""No image exists with the tag "{image_tag_needle}".""",
                fg="red",
            )
            exit(1)

    def get_commit_tag_for_latest_image(image_tags_haystack):
        try:
            filtered = [
                tag for tag in image_tags_haystack if re.match("(commit-[a-f0-9]{7,32})", tag)
            ]
            return filtered[0]
        except IndexError:
            click.secho(
                """The image tagged "latest" does not have a commit tag.""",
                fg="red",
            )
            exit(1)

    image_tags = get_all_tags_for_image(image_tag)

    if image_tag == "latest":
        image_tag = get_commit_tag_for_latest_image(image_tags)

    command = f"IMAGE_TAG={image_tag} copilot svc deploy --env {env} --name {name}"
    click.echo(f"Running: {command}")
    subprocess.call(
        command,
        shell=True,
    )
