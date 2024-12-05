import os

import pytest

from dbt_platform_helper.exceptions import AddonNotFoundError
from dbt_platform_helper.exceptions import AddonTypeMissingFromConfigError
from dbt_platform_helper.exceptions import ApplicationDeploymentNotTriggered
from dbt_platform_helper.exceptions import ApplicationEnvironmentNotFoundError
from dbt_platform_helper.exceptions import ApplicationNotFoundError
from dbt_platform_helper.exceptions import CopilotCodebaseNotFoundError
from dbt_platform_helper.exceptions import CreateTaskTimeoutError
from dbt_platform_helper.exceptions import ECSAgentNotRunning
from dbt_platform_helper.exceptions import ImageNotFoundError
from dbt_platform_helper.exceptions import InvalidAddonTypeError
from dbt_platform_helper.exceptions import NoCopilotCodebasesFoundError
from dbt_platform_helper.exceptions import NotInCodeBaseRepositoryError
from dbt_platform_helper.exceptions import ParameterNotFoundError
from dbt_platform_helper.exceptions import SecretNotFoundError
from dbt_platform_helper.providers.ecs import NoClusterError


@pytest.mark.parametrize(
    "exception, exception_params, expected_message",
    [
        (
            AddonNotFoundError,
            {"addon_name": "test-addon"},
            """Addon "test-addon" does not exist.""",
        ),
        (
            AddonTypeMissingFromConfigError,
            {"addon_name": "test-addon"},
            """The configuration for the addon test-addon, is misconfigured and missing the addon type.""",
        ),
        (
            ApplicationDeploymentNotTriggered,
            {"codebase": "test-codebase"},
            """Your deployment for test-codebase was not triggered.""",
        ),
        (
            ApplicationEnvironmentNotFoundError,
            {"environment": "development"},
            """The environment "development" either does not exist or has not been deployed.""",
        ),
        (
            ApplicationNotFoundError,
            {"application_name": "test-application"},
            """The account "foo" does not contain the application "test-application"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
        ),
        (
            CopilotCodebaseNotFoundError,
            {"codebase": "test-codebase-exists"},
            """The codebase "test-codebase-exists" either does not exist or has not been deployed.""",
        ),
        (
            CreateTaskTimeoutError,
            {
                "addon_name": "test-addon",
                "application_name": "test-application",
                "environment": "environment",
            },
            """Client (test-addon) ECS task has failed to start for "test-application" in "environment" environment.""",
        ),
        (
            InvalidAddonTypeError,
            {"addon_type": "test-addon-type"},
            """Addon type "test-addon-type" is not supported, we support: opensearch, postgres, redis.""",
        ),
        (
            ImageNotFoundError,
            {"commit": "test-commit-hash"},
            """The commit hash "test-commit-hash" has not been built into an image, try the `platform-helper codebase build` command first.""",
        ),
        (
            NoCopilotCodebasesFoundError,
            {"application_name": "test-application"},
            """No codebases found for application "test-application".""",
        ),
        (
            NoClusterError,
            {"application_name": "test-application", "environment": "environment"},
            """No ECS cluster found for "test-application" in "environment" environment.""",
        ),
        (
            NotInCodeBaseRepositoryError,
            {},
            """You are in the deploy repository; make sure you are in the application codebase repository.""",
        ),
        (
            ParameterNotFoundError,
            {"application_name": "test-application", "environment": "environment"},
            """No parameter called "/copilot/applications/test-application/environments/environment/addons". Try deploying the "test-application" "environment" environment.""",
        ),
        (
            SecretNotFoundError,
            {"secret_name": "test-secret"},
            """No secret called "test-secret".""",
        ),
        (
            ECSAgentNotRunning,
            {},
            """ECS exec agent never reached "RUNNING" status""",
        ),
    ],
)
def test_exception_message(exception, exception_params, expected_message):
    os.environ["AWS_PROFILE"] = "foo"

    exception = exception(**exception_params)
    assert str(exception) == expected_message
