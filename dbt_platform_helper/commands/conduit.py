import json
import random
import string
import subprocess
import time
import urllib.parse

import click
from cfn_tools import dump_yaml
from cfn_tools import load_yaml

from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.click import ClickDocOptCommand
from dbt_platform_helper.utils.files import is_terraform_project
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)


class ConduitError(Exception):
    pass


class InvalidAddonTypeConduitError(ConduitError):
    def __init__(self, addon_type):
        self.addon_type = addon_type


class NoClusterConduitError(ConduitError):
    pass


class SecretNotFoundConduitError(ConduitError):
    pass


class CreateTaskTimeoutConduitError(ConduitError):
    pass


class ParameterNotFoundConduitError(ConduitError):
    pass


class AddonNotFoundConduitError(ConduitError):
    pass


CONDUIT_DOCKER_IMAGE_LOCATION = "public.ecr.aws/uktrade/tunnel"
CONDUIT_ADDON_TYPES = [
    "opensearch",
    "rds-postgres",
    "aurora-postgres",
    "postgres",
    "redis",
]
CONDUIT_ACCESS_OPTIONS = ["read", "write", "admin"]


def normalise_secret_name(addon_name: str) -> str:
    return addon_name.replace("-", "_").upper()


def get_addon_type(app: Application, env: str, addon_name: str) -> str:
    session = app.environments[env].session
    ssm_client = session.client("ssm")
    addon_type = None

    try:
        addon_config = json.loads(
            ssm_client.get_parameter(
                Name=f"/copilot/applications/{app.name}/environments/{env}/addons"
            )["Parameter"]["Value"]
        )
    except ssm_client.exceptions.ParameterNotFound:
        raise ParameterNotFoundConduitError

    if addon_name not in addon_config.keys():
        raise AddonNotFoundConduitError

    for name, config in addon_config.items():
        if name == addon_name:
            addon_type = config["type"]

    if not addon_type or addon_type not in CONDUIT_ADDON_TYPES:
        raise InvalidAddonTypeConduitError(addon_type)

    if "postgres" in addon_type:
        addon_type = "postgres"

    return addon_type


def get_parameter_name(
    app: Application, env: str, addon_type: str, addon_name: str, access: str
) -> str:
    if addon_type == "postgres":
        return f"/copilot/{app.name}/{env}/conduits/{normalise_secret_name(addon_name)}_{access.upper()}"
    elif addon_type == "redis" or addon_type == "opensearch":
        return f"/copilot/{app.name}/{env}/conduits/{normalise_secret_name(addon_name)}_ENDPOINT"
    else:
        return f"/copilot/{app.name}/{env}/conduits/{normalise_secret_name(addon_name)}"


def get_or_create_task_name(
    app: Application, env: str, addon_name: str, parameter_name: str
) -> str:
    ssm = app.environments[env].session.client("ssm")

    try:
        return ssm.get_parameter(Name=parameter_name)["Parameter"]["Value"]
    except ssm.exceptions.ParameterNotFound:
        random_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        return f"conduit-{app.name}-{env}-{addon_name}-{random_id}"


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


def update_parameter_with_secret(session, parameter_name, secret_arn):
    ssm_client = session.client("ssm")
    secrets_manager_client = session.client("secretsmanager")
    response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
    parameter_value = response["Parameter"]["Value"]

    parameter_data = json.loads(parameter_value)

    secret_response = secrets_manager_client.get_secret_value(SecretId=secret_arn)
    secret_value = json.loads(secret_response["SecretString"])

    parameter_data["username"] = urllib.parse.quote(secret_value["username"])
    parameter_data["password"] = urllib.parse.quote(secret_value["password"])

    updated_parameter_value = json.dumps(parameter_data)

    return updated_parameter_value


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
    connection_string = update_parameter_with_secret(
        session, read_only_secret_name, master_secret_arn
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


def create_addon_client_task(
    app: Application,
    env: str,
    addon_type: str,
    addon_name: str,
    task_name: str,
    access: str,
):
    secret_name = f"/copilot/{app.name}/{env}/secrets/{normalise_secret_name(addon_name)}"

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

    subprocess.call(
        f"copilot task run --app {app.name} --env {env} "
        f"--task-group-name {task_name} "
        f"--image {CONDUIT_DOCKER_IMAGE_LOCATION}:{addon_type} "
        f"--secrets CONNECTION_SECRET={get_connection_secret_arn(app, env, secret_name)} "
        "--platform-os linux "
        "--platform-arch arm64",
        shell=True,
    )


def addon_client_is_running(app: Application, env: str, cluster_arn: str, task_name: str) -> bool:
    ecs_client = app.environments[env].session.client("ecs")

    tasks = ecs_client.list_tasks(
        cluster=cluster_arn,
        desiredStatus="RUNNING",
        family=f"copilot-{task_name}",
    )

    if not tasks["taskArns"]:
        return False

    described_tasks = ecs_client.describe_tasks(cluster=cluster_arn, tasks=tasks["taskArns"])

    # The ExecuteCommandAgent often takes longer to start running than the task and without the
    # agent it's not possible to exec into a task.
    for task in described_tasks["tasks"]:
        for container in task["containers"]:
            for agent in container["managedAgents"]:
                if agent["name"] == "ExecuteCommandAgent" and agent["lastStatus"] == "RUNNING":
                    return True

    return False


def connect_to_addon_client_task(app: Application, env: str, cluster_arn: str, task_name: str):
    tries = 0
    running = False

    while tries < 15 and not running:
        tries += 1

        if addon_client_is_running(app, env, cluster_arn, task_name):
            running = True
            subprocess.call(
                "copilot task exec "
                f"--app {app.name} --env {env} "
                f"--name {task_name} "
                f"--command bash",
                shell=True,
            )

        time.sleep(1)

    if not running:
        raise CreateTaskTimeoutConduitError


def add_stack_delete_policy_to_task_role(app: Application, env: str, task_name: str):
    session = app.environments[env].session
    cloudformation_client = session.client("cloudformation")
    iam_client = session.client("iam")

    conduit_stack_name = f"task-{task_name}"
    conduit_stack_resources = cloudformation_client.list_stack_resources(
        StackName=conduit_stack_name
    )["StackResourceSummaries"]

    for resource in conduit_stack_resources:
        if resource["LogicalResourceId"] == "DefaultTaskRole":
            task_role_name = resource["PhysicalResourceId"]
            iam_client.put_role_policy(
                RoleName=task_role_name,
                PolicyName="DeleteCloudFormationStack",
                PolicyDocument=json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Action": ["cloudformation:DeleteStack"],
                                "Effect": "Allow",
                                "Resource": f"arn:aws:cloudformation:*:*:stack/{conduit_stack_name}/*",
                            },
                        ],
                    },
                ),
            )


def update_conduit_stack_resources(
    app: Application,
    env: str,
    addon_type: str,
    addon_name: str,
    task_name: str,
    parameter_name: str,
):
    session = app.environments[env].session
    cloudformation_client = session.client("cloudformation")

    conduit_stack_name = f"task-{task_name}"
    template = cloudformation_client.get_template(StackName=conduit_stack_name)
    template_yml = load_yaml(template["TemplateBody"])
    template_yml["Resources"]["LogGroup"]["DeletionPolicy"] = "Retain"
    template_yml["Resources"]["TaskNameParameter"] = load_yaml(
        f"""
        Type: AWS::SSM::Parameter
        Properties:
          Name: {parameter_name}
          Type: String
          Value: {task_name}
        """
    )

    iam_client = session.client("iam")
    log_filter_role_arn = iam_client.get_role(RoleName="CWLtoSubscriptionFilterRole")["Role"]["Arn"]

    ssm_client = session.client("ssm")
    destination_log_group_arns = json.loads(
        ssm_client.get_parameter(Name="/copilot/tools/central_log_groups")["Parameter"]["Value"]
    )

    destination_arn = destination_log_group_arns["dev"]
    if env.lower() in ("prod", "production"):
        destination_arn = destination_log_group_arns["prod"]

    template_yml["Resources"]["SubscriptionFilter"] = load_yaml(
        f"""
        Type: AWS::Logs::SubscriptionFilter
        DeletionPolicy: Retain
        Properties:
          RoleArn: {log_filter_role_arn}
          LogGroupName: /copilot/{task_name}
          FilterName: /copilot/conduit/{app.name}/{env}/{addon_type}/{addon_name}/{task_name.rsplit("-", 1)[1]}
          FilterPattern: ''
          DestinationArn: {destination_arn}
        """
    )

    params = []
    if "Parameters" in template_yml:
        for param in template_yml["Parameters"]:
            params.append({"ParameterKey": param, "UsePreviousValue": True})

    cloudformation_client.update_stack(
        StackName=conduit_stack_name,
        TemplateBody=dump_yaml(template_yml),
        Parameters=params,
        Capabilities=["CAPABILITY_IAM"],
    )


def start_conduit(
    application: Application,
    env: str,
    addon_type: str,
    addon_name: str,
    access: str = "read",
):
    cluster_arn = get_cluster_arn(application, env)
    parameter_name = get_parameter_name(application, env, addon_type, addon_name, access)
    task_name = get_or_create_task_name(application, env, addon_name, parameter_name)

    if not addon_client_is_running(application, env, cluster_arn, task_name):
        create_addon_client_task(application, env, addon_type, addon_name, task_name, access)
        add_stack_delete_policy_to_task_role(application, env, task_name)
        update_conduit_stack_resources(
            application, env, addon_type, addon_name, task_name, parameter_name
        )

    connect_to_addon_client_task(application, env, cluster_arn, task_name)


@click.command(cls=ClickDocOptCommand)
@click.argument("addon_name", type=str, required=True)
@click.option("--app", help="AWS application name", required=True)
@click.option("--env", help="AWS environment name", required=True)
@click.option(
    "--access",
    default="read",
    type=click.Choice(CONDUIT_ACCESS_OPTIONS),
    help="Allow write or admin access to database addons",
)
def conduit(addon_name: str, app: str, env: str, access: str):
    """Create a conduit connection to an addon."""
    check_platform_helper_version_needs_update()
    application = load_application(app)

    try:
        addon_type = get_addon_type(application, env, addon_name)
        start_conduit(application, env, addon_type, addon_name, access)
    except ParameterNotFoundConduitError:
        click.secho(
            f"""No parameter called "/copilot/applications/{app}/environments/{env}/addons". Try deploying the "{app}" "{env}" environment.""",
            fg="red",
        )
        exit(1)
    except AddonNotFoundConduitError:
        click.secho(
            f"""Addon "{addon_name}" does not exist.""",
            fg="red",
        )
        exit(1)
    except InvalidAddonTypeConduitError as err:
        click.secho(
            f"""Addon type "{err.addon_type}" is not supported, we support: {", ".join(CONDUIT_ADDON_TYPES)}.""",
            fg="red",
        )
        exit(1)
    except NoClusterConduitError:
        click.secho(f"""No ECS cluster found for "{app}" in "{env}" environment.""", fg="red")
        exit(1)
    except SecretNotFoundConduitError as err:
        click.secho(
            f"""No secret called "{err}" for "{app}" in "{env}" environment.""",
            fg="red",
        )
        exit(1)
    except CreateTaskTimeoutConduitError:
        click.secho(
            f"""Client ({addon_name}) ECS task has failed to start for "{app}" in "{env}" environment.""",
            fg="red",
        )
        exit(1)
