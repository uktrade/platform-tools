from unittest.mock import Mock

import pytest

from dbt_platform_helper.domain.conduit import Conduit
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import Environment


@pytest.mark.parametrize(
    "app_name, addon_type, addon_name",
    [
        ("app_1", "postgres", "custom-name-postgres"),
        ("app_2", "postgres", "custom-name-rds-postgres"),
        ("app_1", "redis", "custom-name-redis"),
        ("app_1", "opensearch", "custom-name-opensearch"),
    ],
)
def test_conduit(app_name, addon_type, addon_name):

    # mock application
    env = "dev"
    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.list_tasks.return_value = {"taskArns": ["test_arn"], "nextToken": ""}
    sessions = {"000000000": mock_session}
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}
    mock_subprocess = Mock()

    task_name = "task_name"
    cluster_arn = "cluster_arn"

    conduit = Conduit(mock_application, mock_subprocess)

    conduit.start(env)

    mock_session.client.assert_called_once_with("ecs")
    mock_client.list_tasks.assert_called_once_with(
        cluster=cluster_arn,
        desiredStatus="RUNNING",
        family=f"copilot-{task_name}",
    )
    # mock_client.describe_tasks()
    mock_subprocess.call.assert_called_once_with(
        "copilot task exec "
        f"--app {app_name} --env {env} "
        f"--name {task_name} "
        f"--command bash",
        shell=True,
    )


# TODO
# Test retry of client_is_running check
