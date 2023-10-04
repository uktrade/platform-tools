import uuid
from unittest.mock import patch

from click.testing import CliRunner

from dbt_copilot_helper.commands.svc import deploy


@patch("boto3.client")
@patch("subprocess.call")
def test_svc_deploy_with_env_name_and_image_tag_deploys_image_tag(
    subprocess_call, mock_boto_client
):
    """Test that given an env, name and image tag, copilot svc deploy is called
    with values to deploy the specified image to the environment's service."""

    branch_name, commit_hash, env, name = set_up_test_variables()
    mock_describe_images(branch_name, commit_hash, mock_boto_client)

    CliRunner().invoke(
        deploy,
        ["--env", env, "--name", name, "--image-tag", f"commit-{commit_hash}"],
    )

    mock_boto_client.describe_images.assert_not_called()
    subprocess_call.assert_called_once_with(
        f"IMAGE_TAG=commit-{commit_hash} copilot svc deploy --env {env} --name {name}",
        shell=True,
    )


@patch("boto3.client")
@patch("subprocess.call")
def test_svc_deploy_with__latest_deploys_image_tagged_latest(subprocess_call, mock_boto_client):
    """Test that given the image tag latest, copilot svc deploy is called with
    the unique tag of the image currently tagged latest."""

    branch_name, commit_hash, env, name = set_up_test_variables()
    mock_describe_images(branch_name, commit_hash, mock_boto_client)

    CliRunner().invoke(
        deploy,
        ["--env", env, "--name", name, "--image-tag", "latest"],
    )

    mock_boto_client.describe_images.assert_called_once()
    subprocess_call.assert_called_once_with(
        f"IMAGE_TAG=commit-{commit_hash} copilot svc deploy --env {env} --name {name}",
        shell=True,
    )


@patch("boto3.client")
@patch("subprocess.call")
def test_svc_deploy_with__no_image_tag_deploys_image_tagged_latest(
    subprocess_call, mock_boto_client
):
    """Test that given the image tag latest, copilot svc deploy is called with
    the unique tag of the image currently tagged latest."""

    branch_name, commit_hash, env, name = set_up_test_variables()
    mock_describe_images(branch_name, commit_hash, mock_boto_client)

    CliRunner().invoke(
        deploy,
        ["--env", env, "--name", name],
    )

    mock_boto_client.describe_images.assert_called_once()
    subprocess_call.assert_called_once_with(
        f"IMAGE_TAG=commit-{commit_hash} copilot svc deploy --env {env} --name {name}",
        shell=True,
    )

    # TODO: test if the latest tag does not have a commit- tag

    # TODO: test if the tag does not exist

    # TODO: Pass other AWS Copilot flags through...
    # Flags
    #       --allow-downgrade                Optional. Allow using an older version of Copilot to
    #                                        update Copilot components
    #                                        updated by a newer version of Copilot.
    #   -a, --app string                     Name of the application. (default "demodjango")
    #       --detach                         Optional. Skip displaying CloudFormation deployment
    #                                        progress.
    #       --diff                           Compares the generated CloudFormation template to the
    #                                        deployed stack.
    #       --diff-yes                       Skip interactive approval of diff before deploying.
    #   -e, --env string     ALREADY COVERED Name of the environment.
    #       --force                          Optional. Force a new service deployment using the
    #                                        existing image.
    #                                        Not available with the "Static Site" service type.
    #   -h, --help                           help for deploy
    #   -n, --name string    ALREADY COVERED Name of the service.
    #       --no-rollback                    Optional. Disable automatic stack
    #                                        rollback in case of deployment failure.
    #                                        We do not recommend using this flag for a
    #                                        production environment.
    #       --resource-tags stringToString   Optional. Labels with a key and value separated by
    #                                        commas.
    #                                        Allows you to categorize resources. (default [])
    #       --tag string                     Optional. The tag for the container images Copilot
    #                                        builds from Dockerfiles.


def mock_describe_images(branch_name, commit_hash, mock_boto_client):
    mock_boto_client.return_value = mock_boto_client
    mock_boto_client.describe_images.return_value = {
        "imageDetails": [
            {
                "imageTags": [
                    f"commit-{commit_hash}",
                    f"branch-{branch_name}",
                    "latest",
                ]
            }
        ]
    }


def set_up_test_variables():
    hex_string = uuid.uuid4().hex[:7]
    commit_hash = f"{hex_string}"
    branch_name = "does-not-matter"
    env = f"env{hex_string}"
    name = f"name{hex_string}"
    return branch_name, commit_hash, env, name
