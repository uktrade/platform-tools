from unittest.mock import Mock

import pytest

from dbt_platform_helper.domain.conduit import AddonNotFoundConduitError
from dbt_platform_helper.domain.conduit import Conduit
from dbt_platform_helper.domain.conduit import CreateTaskTimeoutConduitError
from dbt_platform_helper.domain.conduit import InvalidAddonTypeConduitError
from dbt_platform_helper.domain.conduit import NoClusterConduitError
from dbt_platform_helper.domain.conduit import ParameterNotFoundConduitError
from dbt_platform_helper.domain.conduit import SecretNotFoundConduitError
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

    conduit.start(env, addon_name)

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


def test_conduit_domain_when_no_cluster_exists():
    # mock application
    app_name = "failed_app"
    addon_name = ""
    env = "dev"

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.list_tasks.return_value = {"taskArns": ["test_arn"], "nextToken": ""}
    sessions = {"000000000": mock_session}
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}

    conduit = Conduit(mock_application)

    with pytest.raises(NoClusterConduitError) as exc:
        conduit.start(env, addon_name)


# TODO when the connection details to the addon does not exist
def test_conduit_domain_when_no_connection_secret_exists():
    app_name = "failed_app"
    addon_name = ""
    env = "dev"

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.list_tasks.return_value = {"taskArns": ["test_arn"], "nextToken": ""}
    sessions = {"000000000": mock_session}
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}
    mock_subprocess = Mock()

    conduit = Conduit(mock_application, mock_subprocess)

    with pytest.raises(SecretNotFoundConduitError) as exc:
        conduit.start(env, addon_name)


def test_conduit_domain_when_client_task_fails_to_start():
    app_name = "failed_app"
    addon_name = ""
    env = "dev"
    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.list_tasks.return_value = {"taskArns": [], "nextToken": ""}
    sessions = {"000000000": mock_session}
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}
    mock_subprocess = Mock()

    conduit = Conduit(mock_application, mock_subprocess)

    with pytest.raises(CreateTaskTimeoutConduitError) as exc:
        conduit.start(env, addon_name)


# TODO conduit requires addon type
def test_conduit_domain_when_addon_type_is_invalid():

    app_name = "failed_app"
    addon_name = "invalid_addon"
    env = "dev"

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.list_tasks.return_value = {"taskArns": [], "nextToken": ""}
    sessions = {"000000000": mock_session}
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}

    conduit = Conduit(mock_application)

    with pytest.raises(InvalidAddonTypeConduitError) as exc:
        conduit.start(env, addon_name)


# TODO conduit requires addon type
def test_conduit_domain_when_addon_does_not_exist():
    app_name = "failed_app"
    addon_name = "addon_doesnt_exist"
    env = "dev"

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.list_tasks.return_value = {"taskArns": [], "nextToken": ""}
    sessions = {"000000000": mock_session}
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}

    conduit = Conduit(mock_application)

    with pytest.raises(AddonNotFoundConduitError) as exc:
        conduit.start(env, addon_name)


# TODO conduit requires addon type
def test_conduit_domain_when_no_addon_config_parameter_exists():
    app_name = "failed_app"
    addon_name = "parameter_doesnt_exist"
    env = "dev"

    mock_client = Mock()
    mock_session = Mock()
    mock_session.client.return_value = mock_client
    mock_client.list_tasks.return_value = {"taskArns": [], "nextToken": ""}
    sessions = {"000000000": mock_session}
    mock_application = Application(app_name)
    mock_application.environments = {env: Environment(env, "000000000", sessions)}

    conduit = Conduit(mock_application)

    with pytest.raises(ParameterNotFoundConduitError) as exc:
        conduit.start(env, addon_name)
