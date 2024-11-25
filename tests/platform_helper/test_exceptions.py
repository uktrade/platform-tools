import pytest

from dbt_platform_helper.exceptions import AddonNotFoundError
from dbt_platform_helper.exceptions import AddonTypeMissingFromConfigError
from dbt_platform_helper.exceptions import CreateTaskTimeoutError
from dbt_platform_helper.exceptions import InvalidAddonTypeError
from dbt_platform_helper.exceptions import NoClusterError
from dbt_platform_helper.exceptions import ParameterNotFoundError
from dbt_platform_helper.exceptions import SecretNotFoundError


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
            """The configuration for the addon test-addon, is missconfigured and missing the addon type.""",
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
            NoClusterError,
            {"application_name": "test-application", "environment": "environment"},
            """No ECS cluster found for "test-application" in "environment" environment.""",
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
    ],
)
def test_exception_message(exception, exception_params, expected_message):
    exception = exception(**exception_params)
    assert str(exception) == expected_message
