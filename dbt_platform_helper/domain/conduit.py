import json
import time

from dbt_platform_helper.providers.subprocess import DBTSubprocess
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.aws import (
    get_postgres_connection_data_updated_with_master_secret,
)
from dbt_platform_helper.utils.platform_config import is_terraform_project


class Conduit:
    def __init__(self, application: Application, subprocess: DBTSubprocess = DBTSubprocess()):
        """

        Args:
            application(Application): an object with the data of the deployed application
        """
        self.application = application
        self.subprocess = subprocess

    def addon_client_is_running(self, env: str, cluster_arn: str, task_name: str):
        ecs_client = self.application.environments[env].session.client("ecs")

        tasks = ecs_client.list_tasks(
            cluster=cluster_arn,
            desiredStatus="RUNNING",
            family=f"copilot-{task_name}",
        )

        if not tasks["taskArns"]:
            return False

        return True

    def start(self, env: str, addon_name: str, addon_type: str, access: str = "read"):
        """
        application: str
        env: str,
        addon_type: str,
        addon_name: str,
        access: str = "read",
        cluster_arn = get_cluster_arn(application, env)
        parameter_name = get_parameter_name(application, env, addon_type, addon_name, access)
        task_name = get_or_create_task_name(application, env, addon_name, parameter_name)

        if not addon_client_is_running(application, env, cluster_arn, task_name):
            create_addon_client_task(application, env, addon_type, addon_name, task_name, access)
            add_stack_delete_policy_to_task_role(application, env, task_name)
            update_conduit_stack_resources(
                application, env, addon_type, addon_name, task_name, parameter_name, access
            )

        connect_to_addon_client_task(application, env, cluster_arn, task_name)
        """

        # task_name = get_or_create_task_name(application, env, addon_name, parameter_name)
        task_name = "task_name"
        cluster_arn = "cluster_arn"
        running = False
        tries = 0

        if not self.addon_client_is_running(env, cluster_arn, task_name):
            create_addon_client_task(
                self.application, env, addon_type, addon_name, task_name, access
            )
            add_stack_delete_policy_to_task_role(self.application, env, task_name)
            update_conduit_stack_resources(
                self.application, env, addon_type, addon_name, task_name, parameter_name, access
            )

        while tries < 15 and not running:
            tries += 1
            if self.addon_client_is_running(env, cluster_arn, task_name):
                running = True
                self.subprocess.call(
                    "copilot task exec "
                    f"--app {self.application.name} --env {env} "
                    f"--name {task_name} "
                    f"--command bash",
                    shell=True,
                )

            time.sleep(1)
        if not running:
            raise CreateTaskTimeoutConduitError


class ConduitError(Exception):
    pass


class CreateTaskTimeoutConduitError(ConduitError):
    pass


class InvalidAddonTypeConduitError(ConduitError):
    def __init__(self, addon_type):
        self.addon_type = addon_type


class NoClusterConduitError(ConduitError):
    pass


class SecretNotFoundConduitError(ConduitError):
    pass


class ParameterNotFoundConduitError(ConduitError):
    pass


class AddonNotFoundConduitError(ConduitError):
    pass


def get_cluster_arn(app: Application, env: str) -> str:
    ecs_client = app.environments[env].session.client("ecs")

    for cluster_arn in ecs_client.list_clusters()["clusterArns"]:
        tags_response = ecs_client.list_tags_for_resource(resourceArn=cluster_arn)
        tags = tags_response["tags"]

        app_key_found = False
        env_key_found = False
        cluster_key_found = False

        for tag in tags:
            if tag["key"] == "copilot-application" and tag["value"] == app.name:
                app_key_found = True
            if tag["key"] == "copilot-environment" and tag["value"] == env:
                env_key_found = True
            if tag["key"] == "aws:cloudformation:logical-id" and tag["value"] == "Cluster":
                cluster_key_found = True

        if app_key_found and env_key_found and cluster_key_found:
            return cluster_arn

    raise NoClusterConduitError


def get_connection_secret_arn(app: Application, env: str, secret_name: str) -> str:
    secrets_manager = app.environments[env].session.client("secretsmanager")
    ssm = app.environments[env].session.client("ssm")

    try:
        return ssm.get_parameter(Name=secret_name, WithDecryption=False)["Parameter"]["ARN"]
    except ssm.exceptions.ParameterNotFound:
        pass

    try:
        return secrets_manager.describe_secret(SecretId=secret_name)["ARN"]
    except secrets_manager.exceptions.ResourceNotFoundException:
        pass

    raise SecretNotFoundConduitError(secret_name)


def create_addon_client_task(
    app: Application,
    env: str,
    addon_type: str,
    addon_name: str,
    task_name: str,
    access: str,
):
    secret_name = f"/copilot/{app.name}/{env}/secrets/{normalise_secret_name(addon_name)}"
    session = app.environments[env].session

    if addon_type == "postgres":
        if access == "read":
            secret_name += "_READ_ONLY_USER"
        elif access == "write":
            secret_name += "_APPLICATION_USER"
        elif access == "admin" and is_terraform_project():
            create_postgres_admin_task(app, env, secret_name, task_name, addon_type, addon_name)
            return
    elif addon_type == "redis" or addon_type == "opensearch":
        secret_name += "_ENDPOINT"

    role_name = f"{addon_name}-{app.name}-{env}-conduitEcsTask"

    try:
        session.client("iam").get_role(RoleName=role_name)
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
        f"copilot task run --app {app.name} --env {env} "
        f"--task-group-name {task_name} "
        f"{execution_role}"
        f"--image {CONDUIT_DOCKER_IMAGE_LOCATION}:{addon_type} "
        f"--secrets CONNECTION_SECRET={get_connection_secret_arn(app, env, secret_name)} "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


def normalise_secret_name(addon_name: str) -> str:
    return addon_name.replace("-", "_").upper()


def create_postgres_admin_task(
    app: Application, env: str, secret_name: str, task_name: str, addon_type: str, addon_name: str
):
    session = app.environments[env].session
    read_only_secret_name = secret_name + "_READ_ONLY_USER"
    master_secret_name = (
        f"/copilot/{app.name}/{env}/secrets/{normalise_secret_name(addon_name)}_RDS_MASTER_ARN"
    )
    master_secret_arn = session.client("ssm").get_parameter(
        Name=master_secret_name, WithDecryption=True
    )["Parameter"]["Value"]
    connection_string = json.dumps(
        get_postgres_connection_data_updated_with_master_secret(
            session, read_only_secret_name, master_secret_arn
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
