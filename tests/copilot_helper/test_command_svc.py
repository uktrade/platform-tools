import os
import shutil
import uuid
from pathlib import Path
from unittest.mock import ANY
from unittest.mock import patch

import botocore.errorfactory
from click.testing import CliRunner

from dbt_copilot_helper.commands.svc import deploy
from tests.copilot_helper.conftest import UTILS_FIXTURES_DIR


@patch("boto3.client")
@patch("subprocess.call")
def test_svc_deploy_with_env_name_repository_and_image_tag_deploys_image_tag(
    subprocess_call, mock_boto_client, tmp_path
):
    """Test that given an env, name, repository and image tag, copilot svc
    deploy is called with values to deploy the specified image to the
    environment's service."""

    branch_name, commit_hash, env, name = set_up_test_variables()
    mock_describe_images_return_tags(branch_name, commit_hash, mock_boto_client)

    os.chdir(tmp_path)
    manifest_dir = Path("copilot") / name
    os.makedirs(manifest_dir)
    shutil.copy(UTILS_FIXTURES_DIR / "test_service_manifest.yml", manifest_dir / "manifest.yml")

    CliRunner().invoke(
        deploy,
        [
            "--env",
            env,
            "--name",
            name,
            "--image-tag",
            f"commit-{commit_hash}",
        ],
    )

    mock_boto_client.describe_images.assert_called_once_with(
        registryId=ANY,
        repositoryName=f"testapp/{name}",
        imageIds=ANY,
    )
    subprocess_call.assert_called_once_with(
        f"IMAGE_TAG=commit-{commit_hash} copilot svc deploy --env {env} --name {name}",
        shell=True,
    )


@patch("boto3.client")
@patch("subprocess.call")
def test_svc_deploy_with_latest_deploys_commit_tag_of_latest_image(
    subprocess_call, mock_boto_client
):
    """Test that given the image tag latest, copilot svc deploy is called with
    the unique commit tag of the image currently tagged latest."""

    branch_name, commit_hash, env, name = set_up_test_variables()
    mock_describe_images_return_tags(branch_name, commit_hash, mock_boto_client)

    CliRunner().invoke(
        deploy,
        ["--env", env, "--name", name, "--image-tag", "latest"],
    )

    mock_boto_client.describe_images.assert_called_once_with(
        registryId=ANY,
        repositoryName=f"testapp/{name}",
        imageIds=ANY,
    )
    subprocess_call.assert_called_once_with(
        f"IMAGE_TAG=commit-{commit_hash} copilot svc deploy --env {env} --name {name}",
        shell=True,
    )


@patch("boto3.client")
@patch("subprocess.call")
def test_svc_deploy_with__no_image_tag_deploys_commit_tag_of_latest_image(
    subprocess_call, mock_boto_client
):
    """Test that given no image tag, copilot svc deploy is called with the
    unique tag of the image currently tagged latest."""

    branch_name, commit_hash, env, name = set_up_test_variables()
    mock_describe_images_return_tags(branch_name, commit_hash, mock_boto_client)

    CliRunner().invoke(
        deploy,
        ["--env", env, "--name", name],
    )

    mock_boto_client.describe_images.assert_called_once_with(
        registryId=ANY,
        repositoryName=f"testapp/{name}",
        imageIds=ANY,
    )
    subprocess_call.assert_called_once_with(
        f"IMAGE_TAG=commit-{commit_hash} copilot svc deploy --env {env} --name {name}",
        shell=True,
    )


@patch("boto3.client")
def test_svc_deploy_with_nonexistent_image_tag_fails_with_message(mock_boto_client):
    """Test that given an image tag which does not exist, it fails with a
    helpful message."""

    branch_name, commit_hash, env, name = set_up_test_variables()
    mock_describe_images_image_not_found(mock_boto_client)
    expected_tag = f"commit-{commit_hash}"

    result = CliRunner().invoke(
        deploy,
        ["--env", env, "--name", name, "--image-tag", expected_tag],
    )

    assert result.exit_code == 1
    assert f"""No image exists with the tag "{expected_tag}".""" in result.stdout


@patch("boto3.client")
def test_svc_deploy_with_latest_but_no_commit_tag_fails_with_message(mock_boto_client):
    """Test that given the image tag latest, where the image tagged latest has
    no commit tag, it fails with a helpful message."""

    branch_name, commit_hash, env, name = set_up_test_variables()
    commit_hash = None
    mock_describe_images_return_tags(branch_name, commit_hash, mock_boto_client)

    result = CliRunner().invoke(
        deploy,
        ["--env", env, "--name", name, "--image-tag", "latest"],
    )

    assert result.exit_code == 1
    assert """The image tagged "latest" does not have a commit tag.""" in result.stdout


@patch("boto3.client")
@patch("subprocess.call")
def test_svc_deploy_with_missing_manifest_file_fails_with_message(
    subprocess_call, mock_boto_client, tmp_path
):
    """If the manifest is missing, display an error message."""
    branch_name, commit_hash, env, name = set_up_test_variables()
    mock_describe_images_return_tags(branch_name, commit_hash, mock_boto_client)

    os.chdir(tmp_path)

    result = CliRunner().invoke(
        deploy,
        [
            "--env",
            env,
            "--name",
            name,
            "--image-tag",
            f"commit-{commit_hash}",
        ],
    )

    mock_boto_client.describe_images.assert_not_called()
    assert result.exit_code == 1
    assert (
        f"Service manifest for {name} could not be found at path copilot/test-service/manifest.yml"
        in result.stdout
    )


@patch("boto3.client")
@patch("subprocess.call")
def test_svc_deploy_with_mismatched_name_in_manifest_file_fails_with_message(
    subprocess_call, mock_boto_client, tmp_path
):
    """If the manifest has a different name than the service name we pass into
    the command, display an error message."""
    branch_name, commit_hash, env, name = set_up_test_variables()
    other_name = "other_name"
    mock_describe_images_return_tags(branch_name, commit_hash, mock_boto_client)

    os.chdir(tmp_path)
    manifest_dir = Path("copilot") / other_name
    os.makedirs(manifest_dir)
    shutil.copy(UTILS_FIXTURES_DIR / "test_service_manifest.yml", manifest_dir / "manifest.yml")

    result = CliRunner().invoke(
        deploy,
        [
            "--env",
            env,
            "--name",
            other_name,
            "--image-tag",
            f"commit-{commit_hash}",
        ],
    )

    mock_boto_client.describe_images.assert_not_called()
    assert result.exit_code == 1
    assert f"Service manifest for {other_name} has name attribute {name}" in result.stdout


@patch("boto3.client")
@patch("subprocess.call")
def test_svc_deploy_with_copilot_bootstrap_image_does_not_change_the_tag(
    subprocess_call, mock_boto_client, tmp_path
):
    """Test that when we specify `...copilot-bootstrap:latest`, the image
    location is left as is."""

    branch_name, commit_hash, env, name = set_up_test_variables()
    mock_describe_images_return_tags(branch_name, commit_hash, mock_boto_client)

    os.chdir(tmp_path)
    manifest_dir = Path("copilot") / name
    os.makedirs(manifest_dir)
    shutil.copy(
        UTILS_FIXTURES_DIR / "test_service_manifest_with_copilot_bootstrap_image.yml",
        manifest_dir / "manifest.yml",
    )

    result = CliRunner().invoke(
        deploy,
        [
            "--env",
            env,
            "--name",
            name,
        ],
    )

    mock_boto_client.describe_images.assert_not_called()
    subprocess_call.assert_called_once_with(
        f"copilot svc deploy --env {env} --name {name}",
        shell=True,
    )


def mock_describe_images_return_tags(branch_name, commit_hash, mock_boto_client):
    mock_boto_client.return_value = mock_boto_client
    image_tags = [
        f"commit-{commit_hash}",
        f"branch-{branch_name}",
        "latest",
    ]
    if not commit_hash:
        del image_tags[0]
    mock_boto_client.describe_images.return_value = {"imageDetails": [{"imageTags": image_tags}]}


def mock_describe_images_image_not_found(mock_boto_client):
    client_exceptions_factory = botocore.errorfactory.ClientExceptionsFactory()
    exception = client_exceptions_factory.create_client_exceptions(
        botocore.session.get_session().get_service_model("ecr")
    ).ImageNotFoundException
    mock_boto_client.return_value.exceptions.ImageNotFoundException = exception
    mock_boto_client.return_value.describe_images.side_effect = exception(
        {
            "Error": {
                "Code": "ImageNotFoundException",
                "Message": "The image requested does not exist in the specified repository.",
            },
        },
        "DescribeImages",
    )


def set_up_test_variables():
    hex_string = uuid.uuid4().hex[:7]
    commit_hash = f"{hex_string}"
    branch_name = "does-not-matter"
    env = f"env{hex_string}"
    name = "test-service"

    return branch_name, commit_hash, env, name
