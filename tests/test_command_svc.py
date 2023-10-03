from unittest.mock import patch

from click.testing import CliRunner
from faker import Faker

from dbt_copilot_helper.commands.svc import deploy

faker = Faker()


@patch("subprocess.call")
def test_svc_deploy_with_env_name_and_image_tag_deploys_image_tag(subprocess_call):
    """Test that given an env, name and image tag, copilot svc deploy is called
    with values to deploy the specified image to the environment's service."""

    random_string = faker.random_letters(length=5)
    tag = f"tag{random_string}"
    env = f"env{random_string}"
    name = f"name{random_string}"

    CliRunner().invoke(
        deploy,
        ["--env", env, "--name", name, "--image-tag", tag],
    )

    subprocess_call.assert_called_once_with(
        f"IMAGE_TAG={tag} copilot svc deploy --env {env} --name {name}",
        shell=True,
    )


@patch("subprocess.call")
def test_svc_deploy_with_env_name_and_latest_deploys_image_tagged_latest(subprocess_call):
    """Test that given the image tag latest, copilot svc deploy is called with
    the unique tag of the image currently tagged latest."""

    random_string = faker.random_letters(length=5)
    expected_tag = f"tag{random_string}"
    env = f"env{random_string}"
    name = f"name{random_string}"

    CliRunner().invoke(
        deploy,
        ["--env", env, "--name", name, "--image-tag", "latest"],
    )

    subprocess_call.assert_called_once_with(
        f"IMAGE_TAG={expected_tag} copilot svc deploy --env {env} --name {name}",
        shell=True,
    )
