import pytest

from dbt_platform_helper.domain.conduit import Conduit
from dbt_platform_helper.utils.application import Application


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
    mock_application = Application(app_name)
    mock_subprocess = Mock()
    env = "dev"
    task_name = "some_task_name"

    conduit = Conduit(mock_application, mock_subprocess)

    conduit.start(env)

    mock_subprocess.assert_called_once_with(
        "copilot task exec "
        f"--app {app_name} --env {env} "
        f"--name {task_name} "
        f"--command bash"
    )
