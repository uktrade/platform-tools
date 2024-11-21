import random
import string

from dbt_platform_helper.exceptions import NoClusterError


# TODO Refactor this to support passing a list of tags to check against, allowing for a more generic implementation
def get_cluster_arn(ecs_client, application_name: str, env: str) -> str:
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


def get_or_create_task_name(
    ssm_client, application_name: str, env: str, addon_name: str, parameter_name: str
) -> str:
    try:
        return ssm_client.get_parameter(Name=parameter_name)["Parameter"]["Value"]
    except ssm_client.exceptions.ParameterNotFound:
        random_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        return f"conduit-{application_name}-{env}-{addon_name}-{random_id}"


# TODO Rename and extract ECS family as parameter / make more general
def addon_client_is_running(ecs_client, cluster_arn: str, task_name: str):
    tasks = ecs_client.list_tasks(
        cluster=cluster_arn,
        desiredStatus="RUNNING",
        family=f"copilot-{task_name}",
    )

    if not tasks["taskArns"]:
        return False

    return True
