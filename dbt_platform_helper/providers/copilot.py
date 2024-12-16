import json
import time

import jinja2
from botocore.exceptions import ClientError

from dbt_platform_helper.constants import CONDUIT_DOCKER_IMAGE_LOCATION
from dbt_platform_helper.providers.aws import CreateTaskTimeoutException
from dbt_platform_helper.providers.secrets import Secrets
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.messages import abort_with_error
from dbt_platform_helper.utils.template import S3_CROSS_ACCOUNT_POLICY
from dbt_platform_helper.utils.template import camel_case
from dbt_platform_helper.utils.template import setup_templates


class CopilotProvider:
    def __init__(self, app: str, templates: jinja2.Environment = None):
        self.app = app
        self.templates = templates if templates else setup_templates()

    def generate_s3_cross_account_service_addons(self, environments, extensions):
        resource_blocks = []
        for ext_name, ext_data in extensions.items():
            for env_name, env_data in ext_data.get("environments", {}).items():
                if "cross_environment_service_access" in env_data:
                    bucket = env_data.get("bucket_name")
                    x_env_data = env_data["cross_environment_service_access"]
                    for access_name, access_data in x_env_data.items():
                        service = access_data.get("service")
                        resource_blocks.append(
                            {
                                "bucket_name": bucket,
                                "appPrefix": camel_case(f"{service}-{bucket}-{access_name}"),
                                "bucket_env": env_name,
                                "access_env": access_data.get("environment"),
                                "bucket_account": environments.get(env_name, {})
                                .get("accounts", {})
                                .get("deploy", {})
                                .get("id"),
                                "read": access_data.get("read", False),
                                "write": access_data.get("write", False),
                            }
                        )

        template = self.templates.get_template(S3_CROSS_ACCOUNT_POLICY)
        contents = template.render({"resources": resource_blocks})

        return contents

    def write_s3_cross_account_service_addons_template(self):
        pass


def create_addon_client_task(
    iam_client,
    ssm_client,
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
            # TODO When we are refactoring this, raise an exception to be caught at the command layer
            abort_with_error(
                f"cannot obtain Role {role_name}: {ex.response.get('Error', {}).get('Message', '')}"
            )

    subprocess.call(
        f"copilot task run --app {application.name} --env {env} "
        f"--task-group-name {task_name} "
        f"{execution_role}"
        f"--image {CONDUIT_DOCKER_IMAGE_LOCATION}:{addon_type} "
        f"--secrets CONNECTION_SECRET={_get_secrets_provider(application, env).get_connection_secret_arn(secret_name)} "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


def create_postgres_admin_task(
    ssm_client,
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
        _get_secrets_provider(app, env).get_postgres_connection_data_updated_with_master_secret(
            read_only_secret_name, master_secret_arn
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


def _temp_until_refactor_get_ecs_task_arns(ecs_client, cluster_arn: str, task_name: str):
    tasks = ecs_client.list_tasks(
        cluster=cluster_arn,
        desiredStatus="RUNNING",
        family=f"copilot-{task_name}",
    )

    if not tasks["taskArns"]:
        return []

    return tasks["taskArns"]


def connect_to_addon_client_task(
    ecs_client,
    subprocess,
    application_name,
    env,
    cluster_arn,
    task_name,
    get_ecs_task_arns=_temp_until_refactor_get_ecs_task_arns,
):
    running = False
    tries = 0
    while tries < 15 and not running:
        tries += 1
        # Todo: Use from ECS provider when we refactor this
        if get_ecs_task_arns(ecs_client, cluster_arn, task_name):
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
        raise CreateTaskTimeoutException(task_name, application_name, env)


def _normalise_secret_name(addon_name: str) -> str:
    return addon_name.replace("-", "_").upper()


def _get_secrets_provider(application: Application, env: str) -> Secrets:
    # Todo: We instantiate the secrets provider here to avoid rabbit holing, but something better probably possible when we are refactoring this area
    return Secrets(
        application.environments[env].session.client("ssm"),
        application.environments[env].session.client("secretsmanager"),
        application.name,
        env,
    )
