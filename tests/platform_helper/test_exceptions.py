import os

import pytest

from dbt_platform_helper.domain.codebase import ApplicationDeploymentNotTriggered
from dbt_platform_helper.domain.codebase import ApplicationEnvironmentNotFoundException
from dbt_platform_helper.domain.codebase import NotInCodeBaseRepositoryException
from dbt_platform_helper.providers.aws.exceptions import IMAGE_NOT_FOUND_TEMPLATE
from dbt_platform_helper.providers.aws.exceptions import MULTIPLE_IMAGES_FOUND_TEMPLATE
from dbt_platform_helper.providers.aws.exceptions import REPOSITORY_NOT_FOUND_TEMPLATE
from dbt_platform_helper.providers.aws.exceptions import (
    CopilotCodebaseNotFoundException,
)
from dbt_platform_helper.providers.aws.exceptions import CreateTaskTimeoutException
from dbt_platform_helper.providers.aws.exceptions import ImageNotFoundException
from dbt_platform_helper.providers.aws.exceptions import LogGroupNotFoundException
from dbt_platform_helper.providers.aws.exceptions import MultipleImagesFoundException
from dbt_platform_helper.providers.aws.exceptions import RepositoryNotFoundException
from dbt_platform_helper.providers.ecs import ECSAgentNotRunningException
from dbt_platform_helper.providers.ecs import NoClusterException
from dbt_platform_helper.providers.secrets import AddonNotFoundException
from dbt_platform_helper.providers.secrets import AddonTypeMissingFromConfigException
from dbt_platform_helper.providers.secrets import InvalidAddonTypeException
from dbt_platform_helper.providers.secrets import ParameterNotFoundException
from dbt_platform_helper.providers.secrets import SecretNotFoundException
from dbt_platform_helper.providers.version_status import UnsupportedVersionException
from dbt_platform_helper.utils.application import ApplicationNotFoundException
from dbt_platform_helper.utils.application import ApplicationServiceNotFoundException


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
            {"application_name": "test-application", "environment": "development"},
            """The environment "development" either does not exist or has not been deployed for the application test-application.""",
        ),
        (
            ApplicationServiceNotFoundException,
            {"application_name": "test-application", "svc_name": "web"},
            """The service web was not found in the application test-application. It either does not exist, or has not been deployed.""",
        ),
        (
            ApplicationNotFoundException,
            {"application_name": "test-application", "environment_name": "test-env"},
            f"""The account "foo" does not contain the application "test-application". 
Please ensure that the environment variable "AWS_PROFILE" is set correctly. If the issue persists, verify that one of the following AWS SSM parameters exists:
 - /platform/applications/test-application/environments/test-env
 - /copilot/applications/test-application""",
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
            {"image_ref": "does-not-exist"},
            IMAGE_NOT_FOUND_TEMPLATE.format(image_ref="does-not-exist"),
        ),
        (
            RepositoryNotFoundException,
            {"repository": "does-not-exist"},
            REPOSITORY_NOT_FOUND_TEMPLATE.format(repository="does-not-exist"),
        ),
        (
            MultipleImagesFoundException,
            {"image_ref": "commit-abc123", "matching_images": ["commit-abc12", "commit-ab"]},
            MULTIPLE_IMAGES_FOUND_TEMPLATE.format(
                image_ref="commit-abc123", matching_images="commit-ab, commit-abc12"
            ),
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
        (
            UnsupportedVersionException,
            {"version": "13.0.0"},
            """Platform-helper version 13.0.0 is not compatible with platform-helper. Please install version platform-helper version 14 or later.""",
        ),
    ],
)
def test_exception_message(exception, exception_params, expected_message):
    os.environ["AWS_PROFILE"] = "foo"

    exception = exception(**exception_params)
    assert str(exception) == expected_message
