import json
import random
import string
import time

from botocore.exceptions import ClientError

from dbt_platform_helper.providers.aws import AWSError
from dbt_platform_helper.providers.aws import get_connection_secret_arn
from dbt_platform_helper.providers.aws import (
    get_postgres_connection_data_updated_with_master_secret,
)
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.messages import abort_with_error

CONDUIT_DOCKER_IMAGE_LOCATION = "public.ecr.aws/uktrade/tunnel"
CONDUIT_ADDON_TYPES = [
    "opensearch",
    "postgres",
    "redis",
]
CONDUIT_ACCESS_OPTIONS = ["read", "write", "admin"]


class NoClusterError(AWSError):
    pass


class CreateTaskTimeoutError(AWSError):
    pass


class ParameterNotFoundError(AWSError):
    pass


class AddonNotFoundError(AWSError):
    pass


class InvalidAddonTypeError(AWSError):
    def __init__(self, addon_type):
        self.addon_type = addon_type


def get_addon_type(ssm_client, application_name: str, env: str, addon_name: str) -> str:
    addon_type = None

    try:
        addon_config = json.loads(
            ssm_client.get_parameter(
                Name=f"/copilot/applications/{application_name}/environments/{env}/addons"
            )["Parameter"]["Value"]
        )
    except ssm_client.exceptions.ParameterNotFound:
        raise ParameterNotFoundError

    if addon_name not in addon_config.keys():
        raise AddonNotFoundError

    for name, config in addon_config.items():
        if name == addon_name:
            addon_type = config["type"]

    if not addon_type or addon_type not in CONDUIT_ADDON_TYPES:
        raise InvalidAddonTypeError(addon_type)

    if "postgres" in addon_type:
        addon_type = "postgres"

    return addon_type


def get_cluster_arn(ecs_client, application_name, env: str) -> str:

    for cluster_arn in ecs_client.list_clusters()["clusterArns"]:
        tags_response = ecs_client.list_tags_for_resource(resourceArn=cluster_arn)
        tags = tags_response["tags"]

        app_key_found = False
        env_key_found = False
        cluster_key_found = False

        for tag in tags:
            if tag["key"] == "copilot-application" and tag["value"] == application_name:
                app_key_found = True
            if tag["key"] == "copilot-environment" and tag["value"] == env:
                env_key_found = True
            if tag["key"] == "aws:cloudformation:logical-id" and tag["value"] == "Cluster":
                cluster_key_found = True

        if app_key_found and env_key_found and cluster_key_found:
            return cluster_arn

    raise NoClusterError


def get_parameter_name(
    application_name: str, env: str, addon_type: str, addon_name: str, access: str
) -> str:
    if addon_type == "postgres":
        return f"/copilot/{application_name}/{env}/conduits/{normalise_secret_name(addon_name)}_{access.upper()}"
    elif addon_type == "redis" or addon_type == "opensearch":
        return f"/copilot/{application_name}/{env}/conduits/{normalise_secret_name(addon_name)}_ENDPOINT"
    else:
        return f"/copilot/{application_name}/{env}/conduits/{normalise_secret_name(addon_name)}"


def get_or_create_task_name(
    ssm_client, application_name: str, env: str, addon_name: str, parameter_name: str
) -> str:

    try:
        return ssm_client.get_parameter(Name=parameter_name)["Parameter"]["Value"]
    except ssm_client.exceptions.ParameterNotFound:
        random_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        return f"conduit-{application_name}-{env}-{addon_name}-{random_id}"


def addon_client_is_running(ecs_client, cluster_arn: str, task_name: str):

    tasks = ecs_client.list_tasks(
        cluster=cluster_arn,
        desiredStatus="RUNNING",
        family=f"copilot-{task_name}",
    )

    if not tasks["taskArns"]:
        return False

    return True


def create_addon_client_task(
    iam_client,
    ssm_client,
    secrets_manager_client,
    subprocess,
    application: Application,
    env: str,
    addon_type: str,
    addon_name: str,
    task_name: str,
    access: str,
):
    secret_name = f"/copilot/{application.name}/{env}/secrets/{normalise_secret_name(addon_name)}"

    if addon_type == "postgres":
        if access == "read":
            secret_name += "_READ_ONLY_USER"
        elif access == "write":
            secret_name += "_APPLICATION_USER"
        elif access == "admin":
            create_postgres_admin_task(
                ssm_client,
                secrets_manager_client,
                subprocess,
                application,
                addon_name,
                addon_type,
                env,
                secret_name,
                task_name,
            )
            return
    elif addon_type == "redis" or addon_type == "opensearch":
        secret_name += "_ENDPOINT"

    role_name = f"{addon_name}-{application.name}-{env}-conduitEcsTask"

    try:
        iam_client.get_role(RoleName=role_name)
        execution_role = f"--execution-role {role_name} "
    except ClientError as ex:
        execution_role = ""
        # We cannot check for botocore.errorfactory.NoSuchEntityException as botocore generates that class on the fly as part of errorfactory.
        # factory. Checking the error code is the recommended way of handling these exceptions.
        if ex.response.get("Error", {}).get("Code", None) != "NoSuchEntity":
            abort_with_error(
                f"cannot obtain Role {role_name}: {ex.response.get('Error', {}).get('Message', '')}"
            )

    subprocess.call(
        f"copilot task run --app {application.name} --env {env} "
        f"--task-group-name {task_name} "
        f"{execution_role}"
        f"--image {CONDUIT_DOCKER_IMAGE_LOCATION}:{addon_type} "
        f"--secrets CONNECTION_SECRET={get_connection_secret_arn(ssm_client,secrets_manager_client, secret_name)} "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


def normalise_secret_name(addon_name: str) -> str:
    return addon_name.replace("-", "_").upper()


def create_postgres_admin_task(
    ssm_client,
    secrets_manager_client,
    subprocess,
    app: Application,
    addon_name: str,
    addon_type: str,
    env: str,
    secret_name: str,
    task_name: str,
):

    read_only_secret_name = secret_name + "_READ_ONLY_USER"
    master_secret_name = (
        f"/copilot/{app.name}/{env}/secrets/{normalise_secret_name(addon_name)}_RDS_MASTER_ARN"
    )
    master_secret_arn = ssm_client.get_parameter(Name=master_secret_name, WithDecryption=True)[
        "Parameter"
    ]["Value"]
    connection_string = json.dumps(
        get_postgres_connection_data_updated_with_master_secret(
            ssm_client, secrets_manager_client, read_only_secret_name, master_secret_arn
        )
    )

    subprocess.call(
        f"copilot task run --app {app.name} --env {env} "
        f"--task-group-name {task_name} "
        f"--image {CONDUIT_DOCKER_IMAGE_LOCATION}:{addon_type} "
        f"--env-vars CONNECTION_SECRET='{connection_string}' "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


def connect_to_addon_client_task(
    ecs_client, subprocess, application_name, env, cluster_arn, task_name
):
    running = False
    tries = 0
    while tries < 15 and not running:
        print("stuck in the loop")
        tries += 1
        if addon_client_is_running(ecs_client, cluster_arn, task_name):
            running = True
            subprocess.call(
                "copilot task exec "
                f"--app {application_name} --env {env} "
                f"--name {task_name} "
                f"--command bash",
                shell=True,
            )

        time.sleep(1)
    if not running:
        raise CreateTaskTimeoutError
