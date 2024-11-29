import json
import time

from botocore.exceptions import ClientError

from dbt_platform_helper.constants import CONDUIT_DOCKER_IMAGE_LOCATION
from dbt_platform_helper.exceptions import CreateTaskTimeoutError
from dbt_platform_helper.providers.ecs import get_ecs_task_arns
from dbt_platform_helper.providers.secrets import get_connection_secret_arn
from dbt_platform_helper.providers.secrets import (
    get_postgres_connection_data_updated_with_master_secret,
)
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.messages import abort_with_error


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
    secret_name = f"/copilot/{application.name}/{env}/secrets/{_normalise_secret_name(addon_name)}"

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
            # TODO Raise an exception to be caught at the command layer
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
        f"/copilot/{app.name}/{env}/secrets/{_normalise_secret_name(addon_name)}_RDS_MASTER_ARN"
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
    ecs_client,
    subprocess,
    application_name,
    env,
    cluster_arn,
    task_name,
    addon_client_is_running_fn=get_ecs_task_arns,
):
    running = False
    tries = 0
    while tries < 15 and not running:
        tries += 1
        if addon_client_is_running_fn(ecs_client, cluster_arn, task_name):
            subprocess.call(
                "copilot task exec "
                f"--app {application_name} --env {env} "
                f"--name {task_name} "
                f"--command bash",
                shell=True,
            )
            running = True

        time.sleep(1)

    if not running:
        raise CreateTaskTimeoutError


def _normalise_secret_name(addon_name: str) -> str:
    return addon_name.replace("-", "_").upper()
