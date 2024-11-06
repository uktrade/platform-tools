from dbt_platform_helper.utils.application import Application


class Conduit:
    def __init__(self, application: Application):
        """

        Args:
            application(Application): an object with the data of the deployed application
        """
        self.application = application

    def start(self):
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


class ConduitError(Exception):
    pass


class NoClusterConduitError(ConduitError):
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
