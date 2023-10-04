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

    # TODO: Patch boto3.client("ecr") to return expected list

    CliRunner().invoke(
        deploy,
        ["--env", env, "--name", name, "--image-tag", "latest"],
    )

    subprocess_call.assert_called_once_with(
        f"IMAGE_TAG={expected_tag} copilot svc deploy --env {env} --name {name}",
        shell=True,
    )

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
