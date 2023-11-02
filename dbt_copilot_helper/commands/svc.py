#!/usr/bin/env python

import re
import subprocess
from pathlib import Path

import boto3
import click

from dbt_copilot_helper.utils.click import ClickDocOptGroup
from dbt_copilot_helper.utils.manifests import get_repository_name_from_manifest
from dbt_copilot_helper.utils.manifests import get_service_name_from_manifest
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
    """Deploy image tag to a service, defaults to image tagged latest."""

    deploy_command = f"copilot svc deploy --env {env} --name {name}"

    repository_name = validate_service_manifest_and_return_repository(name)

    if repository_name != "uktrade/copilot-bootstrap":
        image_tags = get_all_tags_for_image(image_tag, repository_name)

        if image_tag == "latest":
            image_tag = get_commit_tag_for_latest_image(image_tags)

        deploy_command = f"IMAGE_TAG={image_tag} {deploy_command}"

    click.echo(f"Running: {deploy_command}")
    subprocess.call(
        deploy_command,
        shell=True,
    )


def get_all_tags_for_image(image_tag_needle, repository_name):
    registry_id = boto3.client("sts").get_caller_identity()["Account"]
    ecr_client = boto3.client("ecr")
    try:
        response = ecr_client.describe_images(
            registryId=registry_id,
            repositoryName=repository_name,
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
        filtered = [tag for tag in image_tags_haystack if re.match("(commit-[a-f0-9]{7,32})", tag)]
        return filtered[0]
    except IndexError:
        click.secho(
            """The image tagged "latest" does not have a commit tag.""",
            fg="red",
        )
        exit(1)


def validate_service_manifest_and_return_repository(name):
    service_manifest = Path("copilot") / name / "manifest.yml"
    try:
        service_name_in_manifest = get_service_name_from_manifest(service_manifest)
        if service_name_in_manifest != name:
            click.secho(
                f"Service manifest for {name} has name attribute {service_name_in_manifest}",
                fg="red",
            )
            exit(1)
    except FileNotFoundError:
        click.secho(
            f"Service manifest for {name} could not be found at path {service_manifest}", fg="red"
        )
        exit(1)

    return get_repository_name_from_manifest(service_manifest)
