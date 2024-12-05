import os

import pytest

from dbt_platform_helper.domain.codebase import ApplicationDeploymentNotTriggered
from dbt_platform_helper.domain.codebase import ApplicationEnvironmentNotFoundException
from dbt_platform_helper.domain.codebase import NotInCodeBaseRepositoryException
from dbt_platform_helper.providers.aws import CopilotCodebaseNotFoundException
from dbt_platform_helper.providers.aws import CreateTaskTimeoutException
from dbt_platform_helper.providers.aws import ImageNotFoundException
from dbt_platform_helper.providers.aws import LogGroupNotFoundException
from dbt_platform_helper.providers.ecs import ECSAgentNotRunningException
from dbt_platform_helper.providers.ecs import NoClusterException
from dbt_platform_helper.providers.secrets import AddonNotFoundException
from dbt_platform_helper.providers.secrets import AddonTypeMissingFromConfigException
from dbt_platform_helper.providers.secrets import InvalidAddonTypeException
from dbt_platform_helper.providers.secrets import ParameterNotFoundException
from dbt_platform_helper.providers.secrets import SecretNotFoundException
from dbt_platform_helper.utils.application import ApplicationNotFoundException


@pytest.mark.parametrize(
    "exception, exception_params, expected_message",
    [
        (
            AddonNotFoundException,
            {"addon_name": "test-addon"},
            """Addon "test-addon" does not exist.""",
        ),
        (
            AddonTypeMissingFromConfigException,
            {"addon_name": "test-addon"},
            """The configuration for the addon test-addon, is misconfigured and missing the addon type.""",
        ),
        (
            ApplicationDeploymentNotTriggered,
            {"codebase": "test-codebase"},
            """Your deployment for test-codebase was not triggered.""",
        ),
        (
            ApplicationEnvironmentNotFoundException,
            {"environment": "development"},
            """The environment "development" either does not exist or has not been deployed.""",
        ),
        (
            ApplicationNotFoundException,
            {"application_name": "test-application"},
            """The account "foo" does not contain the application "test-application"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
        ),
        (
            CopilotCodebaseNotFoundException,
            {"codebase": "test-codebase-exists"},
            """The codebase "test-codebase-exists" either does not exist or has not been deployed.""",
        ),
        (
            CreateTaskTimeoutException,
            {
                "addon_name": "test-addon",
                "application_name": "test-application",
                "environment": "environment",
            },
            """Client (test-addon) ECS task has failed to start for "test-application" in "environment" environment.""",
        ),
        (
            InvalidAddonTypeException,
            {"addon_type": "test-addon-type"},
            """Addon type "test-addon-type" is not supported, we support: opensearch, postgres, redis.""",
        ),
        (
            ImageNotFoundException,
            {"commit": "test-commit-hash"},
            """The commit hash "test-commit-hash" has not been built into an image, try the `platform-helper codebase build` command first.""",
        ),
        (
            LogGroupNotFoundException,
            {"log_group_name": "test-log-group"},
            """No log group called "test-log-group".""",
        ),
        (
            NoClusterException,
            {"application_name": "test-application", "environment": "environment"},
            """No ECS cluster found for "test-application" in "environment" environment.""",
        ),
        (
            NotInCodeBaseRepositoryException,
            {},
            """You are in the deploy repository; make sure you are in the application codebase repository.""",
        ),
        (
            ParameterNotFoundException,
            {"application_name": "test-application", "environment": "environment"},
            """No parameter called "/copilot/applications/test-application/environments/environment/addons". Try deploying the "test-application" "environment" environment.""",
        ),
        (
            SecretNotFoundException,
            {"secret_name": "test-secret"},
            """No secret called "test-secret".""",
        ),
        (
            ECSAgentNotRunningException,
            {},
            """ECS exec agent never reached "RUNNING" status""",
        ),
    ],
)
def test_exception_message(exception, exception_params, expected_message):
    os.environ["AWS_PROFILE"] = "foo"

    exception = exception(**exception_params)
    assert str(exception) == expected_message
