from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import create_autospec

import pytest

from dbt_platform_helper.domain.update_alb_rules import UpdateALBRules
from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.version import InstalledVersionProvider


@pytest.mark.parametrize(
    "input_args, expected_results, expect_exception",
    [
        (
            {
                "environment": "production",
            },
            ["Deployment Mode: copilot", "ARN: alb-arn-doesnt-matter"],
            False,
        ),
        (
            {
                "environment": "development",
            },
            ["Deployment Mode: dual-deploy-copilot-traffic", "ARN: listener-arn-doesnt-matter"],
            False,
        ),
        (
            {
                "environment": "test",
            },
            ["Deployment Mode: dual-deploy-platform-traffic", "ARN: listener-arn-doesnt-matter"],
            False,
        ),
        (
            {
                "environment": "staging",
            },
            ["Deployment Mode: platform", "ARN: alb-arn-doesnt-matter"],
            False,
        ),
    ],
)
def test_alb_rules(
    fakefs,
    create_valid_platform_config_file,
    mock_application,
    input_args,
    expected_results,
    expect_exception,
):

    load_application = Mock()
    load_application.return_value = mock_application
    mock_installed_version_provider = create_autospec(spec=InstalledVersionProvider, spec_set=True)
    mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(14, 0, 0)
    mock_config_validator = Mock(spec=ConfigValidator)
    mock_config_provider = ConfigProvider(
        mock_config_validator, installed_version_provider=mock_installed_version_provider
    )

    mock_session = mock_application.environments[input_args["environment"]].session

    mock_boto_elbv2_client = Mock(name="client-mock")
    mock_boto_elbv2_client.get_paginator.return_value.paginate.return_value = [
        {
            "LoadBalancers": [
                {
                    "LoadBalancerArn": "alb-arn-doesnt-matter",
                },
            ],
            "NextMarker": "string",
        }
    ]
    mock_boto_elbv2_client.describe_tags.return_value = {
        "TagDescriptions": [
            {
                "ResourceArn": "alb-arn-doesnt-matter",
                "Tags": [
                    {"Key": "copilot-application", "Value": "test-application"},
                    {"Key": "copilot-environment", "Value": input_args["environment"]},
                ],
            },
        ]
    }
    mock_session = Mock(name="session-mock")
    mock_session.client.return_value = mock_boto_elbv2_client

    mock_io = MagicMock()

    update_aws = UpdateALBRules(
        mock_session,
        config_provider=mock_config_provider,
        io=mock_io,
        load_application=load_application,
    )

    update_aws.update_alb_rules(
        **input_args,
    )  # load_balancer=alb_provider

    mock_io.info.assert_has_calls([call(result) for result in expected_results])
