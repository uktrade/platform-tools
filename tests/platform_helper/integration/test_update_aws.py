from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import create_autospec

import pytest
from botocore.exceptions import ClientError

from dbt_platform_helper.domain.update_alb_rules import UpdateALBRules
from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.version import InstalledVersionProvider


class ALBRulesTestFixtures:

    @staticmethod
    def create_rule_response(
        arn_index,
        priority,
        path_pattern=["/*"],
        host_header="web.doesnt-matter",
        http_headers=[],
        source_ip=False,
    ):
        conditions = [
            {
                "Field": "host-header",
                "Values": [host_header],
                "HostHeaderConfig": {"Values": [host_header]},
            }
        ]

        for header in http_headers:
            if header == "bypass-key":
                conditions.append(
                    {
                        "Field": "http-header",
                        "HttpHeaderConfig": {
                            "HttpHeaderName": "Bypass-Key",
                            "Values": ["xxxxxxxx"],
                        },
                    },
                )
            elif header == "forward":
                conditions.append(
                    {
                        "Field": "http-header",
                        "HttpHeaderConfig": {
                            "HttpHeaderConfig": {
                                "HttpHeaderName": "X-Forwarded-For",
                                "Values": ["10.10.10.100"],
                            },
                        },
                    },
                )

        if source_ip:
            conditions.append(
                {
                    "Field": "http-header",
                    "HttpHeaderConfig": {
                        "HttpHeaderConfig": {
                            "HttpHeaderName": "X-Forwarded-For",
                            "Values": ["10.10.10.100"],
                        },
                    },
                },
            )

        if path_pattern:
            conditions.append(
                {
                    "Field": "path-pattern",
                    "Values": path_pattern if isinstance(path_pattern, list) else [path_pattern],
                    "PathPatternConfig": {
                        "Values": path_pattern if isinstance(path_pattern, list) else [path_pattern]
                    },
                }
            )

        return {
            "RuleArn": f"listener-rule-arn-doesnt-matter-{arn_index}",
            "Priority": f"{priority}",
            "Conditions": conditions,
            "Actions": [
                {
                    "Type": "forward",
                    "TargetGroupArn": f"tg-arn-doesnt-matter-{arn_index}",
                    "ForwardConfig": {
                        "TargetGroups": [
                            {"TargetGroupArn": f"tg-arn-doesnt-matter-{arn_index}", "Weight": 1}
                        ],
                        "TargetGroupStickiness": {"Enabled": False},
                    },
                }
            ],
            "IsDefault": False,
            "ResourceArn": f"listener-rule-arn-doesnt-matter-{arn_index}",
        }

    @staticmethod
    def create_target_group(arn_suffix, healthcheck_path="/"):
        base_tg = {
            "TargetGroupArn": f"tg-arn-doesnt-matter-{arn_suffix}",
            "TargetGroupName": f"doesnt-matter-{arn_suffix}",
            "Protocol": "HTTPS",
            "Port": 443,
            "VpcId": "vpc-xxxxxxxxx",
            "HealthCheckProtocol": "HTTP",
            "HealthCheckPort": "8080",
            "HealthCheckEnabled": True,
            "HealthCheckIntervalSeconds": 35,
            "HealthCheckTimeoutSeconds": 30,
            "HealthyThresholdCount": 3,
            "UnhealthyThresholdCount": 3,
            "HealthCheckPath": "/",
            "Matcher": {"HttpCode": "200"},
            "LoadBalancerArns": ["alb-arn-doesnt-matter"],
            "TargetType": "ip",
            "ProtocolVersion": "HTTP1",
            "IpAddressType": "ipv4",
        }

        if healthcheck_path != "/":
            base_tg.update(
                {
                    "HealthCheckEnabled": False,
                    "HealthCheckPath": str(healthcheck_path),
                    "Matcher": {"HttpCode": "200,301,302"},
                }
            )

        return base_tg

    @staticmethod
    def create_tag_descriptions(arn, tags={}):
        return {
            "ResourceArn": arn,
            "Tags": [{"Key": key, "Value": value} for key, value in tags.items()],
        }


class MockALBService:

    def __init__(self, environment, create_platform_rules=False):
        self.environment = environment
        self.create_platform_rules = create_platform_rules
        self.fixtures = ALBRulesTestFixtures()

        self._paginators = {}  # Store the mock so it doesn't get recreated each time

    def create_elbv2_client_mock(self):
        mock_client = Mock(name="elbv2-client-mock")

        mock_client.get_paginator.side_effect = self._get_paginator

        mock_client.describe_tags = self._create_tag_descriptions()

        return mock_client

    def _get_paginator(self, operation_name):
        if operation_name not in self._paginators:
            if operation_name == "describe_load_balancers":
                self._paginators[operation_name] = self._create_lb_paginator()
            elif operation_name == "describe_listeners":
                self._paginators[operation_name] = self._create_listener_paginator()
            elif operation_name == "describe_rules":
                self._paginators[operation_name] = self._create_describe_rules_paginator()
            elif operation_name == "describe_target_groups":
                self._paginators[operation_name] = self._create_describe_target_groups_paginator()
            else:
                self._paginators[operation_name] = Mock()

        return self._paginators[operation_name]

    def _create_lb_paginator(self):
        paginator = Mock()
        paginator.paginate.return_value = [
            {
                "LoadBalancers": [
                    {
                        "LoadBalancerArn": "alb-arn-doesnt-matter",
                    },
                ],
                "NextMarker": "string",
            }
        ]
        return paginator

    def _create_listener_paginator(self):
        paginator = Mock()
        paginator.paginate.return_value = [
            {
                "Listeners": [
                    {
                        "ListenerArn": "listener-arn-doesnt-matter",
                        "LoadBalancerArn": "alb-arn-doesnt-matter",
                        "Port": 123,
                        "Protocol": "HTTPS",
                    },
                ],
                "NextMarker": "string",
            }
        ]
        return paginator

    def _create_describe_rules_paginator(self):
        paginator = Mock()

        rules = [
            # Maintence page rules example
            self.fixtures.create_rule_response(1, "1", http_headers=["forward"]),
            self.fixtures.create_rule_response(2, "2", source_ip=True),
            self.fixtures.create_rule_response(3, "3", http_headers=["bypass-key"]),
            # Copilot rules >48000
            self.fixtures.create_rule_response(
                4, "48000", path_pattern=["/secondary-service/*", "/secondary-service"]
            ),
            self.fixtures.create_rule_response(5, "49000", host_header="api.doesnt-matter"),
            self.fixtures.create_rule_response(6, "50000"),
            self.fixtures.create_rule_response(7, "default"),
        ]

        if self.create_platform_rules:
            # Platform rules
            rules.extend(
                [
                    self.fixtures.create_rule_response(
                        8, "10000", path_pattern=["/secondary-service/*", "/secondary-service"]
                    ),
                    self.fixtures.create_rule_response(9, "10100"),
                    self.fixtures.create_rule_response(
                        10, "11000", host_header="api.doesnt-matter"
                    ),
                ]
            )
        paginator.paginate.return_value = [
            {
                "Rules": rules,
                "NextMarker": "string",
            }
        ]
        return paginator

    def _create_describe_target_groups_paginator(self):
        """
        This function for target groups is called multiple times.

        Each item in the side effect is returned each call
        """
        paginator = Mock()
        paginator.paginate = Mock(
            side_effect=[
                [
                    {
                        "TargetGroups": [
                            self.fixtures.create_target_group(4, "/secondary-service"),
                            self.fixtures.create_target_group(5),
                            self.fixtures.create_target_group(6),
                            self.fixtures.create_target_group(7, "/doesnt-matter"),
                            self.fixtures.create_target_group(8, "/secondary-service"),
                            self.fixtures.create_target_group(9),
                            self.fixtures.create_target_group(10),
                        ],
                        "NextMarker": "string",
                    },
                ],
                [
                    {
                        "TargetGroups": [
                            self.fixtures.create_target_group(4, "/secondary-service"),
                        ],
                        "NextMarker": "string",
                    },
                ],
                [
                    {
                        "TargetGroups": [
                            self.fixtures.create_target_group(5),
                        ],
                        "NextMarker": "string",
                    },
                ],
                [
                    {
                        "TargetGroups": [
                            self.fixtures.create_target_group(6),
                        ],
                        "NextMarker": "string",
                    }
                ],
            ]
        )
        return paginator

    def _create_tag_descriptions(self):
        """Order is based on the order they are called so it is very important
        for boto3 calls."""

        platform_rule_tags = []
        if self.create_platform_rules:
            platform_rule_tags.extend(
                [
                    self.fixtures.create_tag_descriptions(
                        "listener-rule-arn-doesnt-matter-8",
                        {
                            "application": "test-application",
                            "environment": self.environment,
                            "service": "web-path",
                            "reason": "service",
                            "managed-by": "DBT Platform",
                        },
                    ),
                    self.fixtures.create_tag_descriptions(
                        "listener-rule-arn-doesnt-matter-9",
                        {
                            "application": "test-application",
                            "environment": self.environment,
                            "service": "web",
                            "reason": "service",
                            "managed-by": "DBT Platform",
                        },
                    ),
                    self.fixtures.create_tag_descriptions(
                        "listener-rule-arn-doesnt-matter-10",
                        {
                            "application": "test-application",
                            "environment": self.environment,
                            "service": "api",
                            "reason": "service",
                            "managed-by": "DBT Platform",
                        },
                    ),
                ]
            )
        return Mock(
            side_effect=[
                {  # ALB
                    "TagDescriptions": [
                        self.fixtures.create_tag_descriptions(
                            "alb-arn-doesnt-matter",
                            {
                                "copilot-application": "test-application",
                                "copilot-environment": self.environment,
                            },
                        )
                    ]
                },
                {  # Listener rule tags
                    "TagDescriptions": [
                        self.fixtures.create_tag_descriptions(
                            "listener-rule-arn-doesnt-matter-1",
                            {"name": "AllowedIps", "service": "web"},
                        ),
                        self.fixtures.create_tag_descriptions(
                            "listener-rule-arn-doesnt-matter-2",
                            {"name": "AllowedSourceIps", "service": "web"},
                        ),
                        self.fixtures.create_tag_descriptions(
                            "listener-rule-arn-doesnt-matter-3",
                            {"name": "BypassIpFilter", "service": "web"},
                        ),
                        self.fixtures.create_tag_descriptions(
                            "listener-rule-arn-doesnt-matter-4",
                        ),
                        self.fixtures.create_tag_descriptions(
                            "listener-rule-arn-doesnt-matter-5",
                        ),
                        self.fixtures.create_tag_descriptions(
                            "listener-rule-arn-doesnt-matter-6",
                        ),
                        self.fixtures.create_tag_descriptions(
                            "listener-rule-arn-doesnt-matter-7",
                        ),
                        *platform_rule_tags,
                    ]
                },
                {  # Target group tags
                    "TagDescriptions": [
                        self.fixtures.create_tag_descriptions(
                            "tg-arn-doesnt-matter-8",
                            {
                                "environment": self.environment,
                                "application": "test-application",
                                "managed-by": "DBT Platform - Service Terraform",
                                "service": "web-path",
                            },
                        ),
                        self.fixtures.create_tag_descriptions(
                            "tg-arn-doesnt-matter-9",
                            {
                                "environment": self.environment,
                                "application": "test-application",
                                "managed-by": "DBT Platform - Service Terraform",
                                "service": "web",
                            },
                        ),
                        self.fixtures.create_tag_descriptions(
                            "tg-arn-doesnt-matter-10",
                            {
                                "environment": self.environment,
                                "application": "test-application",
                                "managed-by": "DBT Platform - Service Terraform",
                                "service": "api",
                            },
                        ),
                        self.fixtures.create_tag_descriptions(
                            "tg-arn-doesnt-matter-99",
                            {
                                "environment": "different-env",
                                "application": "test-application",
                                "managed-by": "DBT Platform - Service Terraform",
                                "service": "web",
                            },
                        ),
                        self.fixtures.create_tag_descriptions(
                            "tg-arn-doesnt-matter-98",
                            {
                                "environment": self.environment,
                                "application": "different-application",
                                "managed-by": "DBT Platform - Service Terraform",
                                "service": "web",
                            },
                        ),
                        self.fixtures.create_tag_descriptions(
                            "tg-arn-doesnt-matter-97",
                            {
                                "copilot-application": "test-application",
                                "copilot-environment": self.environment,
                                "environment": self.environment,
                                "application": "test-application",
                                "managed-by": "DBT Platform - Terraform",
                            },
                        ),
                        self.fixtures.create_tag_descriptions(
                            "tg-arn-doesnt-matter-4",
                            {
                                "copilot-application": "test-application",
                                "copilot-environment": self.environment,
                                "copilot-service": "web-path",
                            },
                        ),
                        self.fixtures.create_tag_descriptions(
                            "tg-arn-doesnt-matter-5",
                            {
                                "copilot-application": "test-application",
                                "copilot-environment": self.environment,
                                "copilot-service": "api",
                            },
                        ),
                        self.fixtures.create_tag_descriptions(
                            "tg-arn-doesnt-matter-6",
                            {
                                "copilot-application": "test-application",
                                "copilot-environment": self.environment,
                                "copilot-service": "web",
                            },
                        ),
                        self.fixtures.create_tag_descriptions(
                            "tg-arn-doesnt-matter-7",
                        ),
                    ]
                },
                {
                    "TagDescriptions": [
                        self.fixtures.create_tag_descriptions(
                            "tg-arn-doesnt-matter-4",
                            {
                                "copilot-application": "test-application",
                                "copilot-environment": self.environment,
                                "copilot-service": "web-path",
                            },
                        ),
                    ]
                },
                {
                    "TagDescriptions": [
                        self.fixtures.create_tag_descriptions(
                            "tg-arn-doesnt-matter-5",
                            {
                                "copilot-application": "test-application",
                                "copilot-environment": self.environment,
                                "copilot-service": "api",
                            },
                        ),
                    ]
                },
                {
                    "TagDescriptions": [
                        self.fixtures.create_tag_descriptions(
                            "tg-arn-doesnt-matter-6",
                            {
                                "copilot-application": "test-application",
                                "copilot-environment": self.environment,
                                "copilot-service": "web",
                            },
                        ),
                    ]
                },
            ]
        )


@pytest.mark.parametrize(
    "input_args, expected_results, create_platform_rules, assert_created_rules",
    [
        (
            {
                "environment": "production",
            },
            [
                "Deployment Mode: copilot",
                "ARN: listener-arn-doesnt-matter",
                "Deleted existing rule: listener-rule-arn-doesnt-matter-8",
                "Deleted existing rule: listener-rule-arn-doesnt-matter-9",
                "Deleted existing rule: listener-rule-arn-doesnt-matter-10",
                "Deleted rules: ['listener-rule-arn-doesnt-matter-8', 'listener-rule-arn-doesnt-matter-9', 'listener-rule-arn-doesnt-matter-10']",
            ],
            True,
            False,
        ),
        (
            {
                "environment": "development",
            },
            [
                "Deployment Mode: dual-deploy-copilot-traffic",
                "ARN: listener-arn-doesnt-matter",
                "Deleted existing rule: listener-rule-arn-doesnt-matter-8",
                "Deleted existing rule: listener-rule-arn-doesnt-matter-9",
                "Deleted existing rule: listener-rule-arn-doesnt-matter-10",
                "Deleted rules: ['listener-rule-arn-doesnt-matter-8', 'listener-rule-arn-doesnt-matter-9', 'listener-rule-arn-doesnt-matter-10']",
            ],
            True,
            False,
        ),
        (
            {
                "environment": "test",
            },
            [
                "Deployment Mode: dual-deploy-platform-traffic",
                "ARN: listener-arn-doesnt-matter",
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-4",
                "Updated forward action for service web-path to use: tg-arn-doesnt-matter-8",
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-5",
                "Updated forward action for service api to use: tg-arn-doesnt-matter-10",
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-6",
                "Updated forward action for service web to use: tg-arn-doesnt-matter-9",
                "Creating platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-4",
                "Creating platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-6",
                "Creating platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-5",
                "Created rules: ['platform-new-web-path-arn', 'platform-new-web-arn', 'platform-new-api-arn']",
            ],
            False,
            True,
        ),
        (
            {
                "environment": "test",
            },
            [
                "Deployment Mode: dual-deploy-platform-traffic",
                "ARN: listener-arn-doesnt-matter",
                "Deleted existing rule: listener-rule-arn-doesnt-matter-8",
                "Deleted existing rule: listener-rule-arn-doesnt-matter-9",
                "Deleted existing rule: listener-rule-arn-doesnt-matter-10",
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-4",
                "Updated forward action for service web-path to use: tg-arn-doesnt-matter-8",
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-5",
                "Updated forward action for service api to use: tg-arn-doesnt-matter-10",
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-6",
                "Updated forward action for service web to use: tg-arn-doesnt-matter-9",
                "Creating platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-4",
                "Creating platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-6",
                "Creating platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-5",
                "Created rules: ['platform-new-web-path-arn', 'platform-new-web-arn', 'platform-new-api-arn']",
                "Deleted rules: ['listener-rule-arn-doesnt-matter-8', 'listener-rule-arn-doesnt-matter-9', 'listener-rule-arn-doesnt-matter-10']",
            ],
            True,  # platform rules exist so deleted and re-created
            True,
        ),
        (
            {
                "environment": "staging",
            },
            [
                "Deployment Mode: platform",
                "ARN: listener-arn-doesnt-matter",
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-4",
                "Updated forward action for service web-path to use: tg-arn-doesnt-matter-8",
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-5",
                "Updated forward action for service api to use: tg-arn-doesnt-matter-10",
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-6",
                "Updated forward action for service web to use: tg-arn-doesnt-matter-9",
                "Creating platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-4",
                "Creating platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-6",
                "Creating platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-5",
                "Created rules: ['platform-new-web-path-arn', 'platform-new-web-arn', 'platform-new-api-arn']",
            ],
            False,
            True,
        ),
    ],
)
def test_alb_rules(
    fakefs,
    create_valid_platform_config_file,
    mock_application,
    input_args,
    expected_results,
    create_platform_rules,
    assert_created_rules,
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

    mock_alb = MockALBService(
        environment=input_args["environment"], create_platform_rules=create_platform_rules
    )
    mock_boto_elbv2_client = mock_alb.create_elbv2_client_mock()

    if assert_created_rules:
        mock_boto_elbv2_client.create_rule = Mock(
            side_effect=[
                {"Rules": [{"RuleArn": "platform-new-web-path-arn"}]},
                {"Rules": [{"RuleArn": "platform-new-web-arn"}]},
                {"Rules": [{"RuleArn": "platform-new-api-arn"}]},
            ]
        )

    if create_platform_rules:
        mock_boto_elbv2_client.delete_rule = Mock(
            side_effect=[
                {"Rules": [{"RuleArn": "listener-rule-arn-doesnt-matter-8"}]},
                {"Rules": [{"RuleArn": "listener-rule-arn-doesnt-matter-9"}]},
                {"Rules": [{"RuleArn": "listener-rule-arn-doesnt-matter-10"}]},
            ]
        )

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
    )

    mock_io.info.assert_has_calls([call(result) for result in expected_results])

    if assert_created_rules:
        mock_boto_elbv2_client.create_rule.assert_has_calls(
            [
                call(
                    ListenerArn="listener-arn-doesnt-matter",
                    Priority=10000,
                    Conditions=[
                        {"Field": "host-header", "Values": ["web.doesnt-matter"]},
                        {
                            "Field": "path-pattern",
                            "Values": ["/secondary-service/*", "/secondary-service"],
                        },
                    ],
                    Actions=[
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-8",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter-8", "Weight": 1}
                                ],
                                "TargetGroupStickiness": {"Enabled": False},
                            },
                        }
                    ],
                    Tags=[
                        {"Key": "application", "Value": "test-application"},
                        {"Key": "environment", "Value": input_args["environment"]},
                        {"Key": "service", "Value": "web-path"},
                        {"Key": "reason", "Value": "service"},
                        {"Key": "managed-by", "Value": "DBT Platform"},
                    ],
                ),
                call(
                    ListenerArn="listener-arn-doesnt-matter",
                    Priority=10100,
                    Conditions=[
                        {"Field": "host-header", "Values": ["web.doesnt-matter"]},
                        {"Field": "path-pattern", "Values": ["/*"]},
                    ],
                    Actions=[
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-9",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter-9", "Weight": 1}
                                ],
                                "TargetGroupStickiness": {"Enabled": False},
                            },
                        }
                    ],
                    Tags=[
                        {"Key": "application", "Value": "test-application"},
                        {"Key": "environment", "Value": input_args["environment"]},
                        {"Key": "service", "Value": "web"},
                        {"Key": "reason", "Value": "service"},
                        {"Key": "managed-by", "Value": "DBT Platform"},
                    ],
                ),
                call(
                    ListenerArn="listener-arn-doesnt-matter",
                    Priority=11000,
                    Conditions=[
                        {"Field": "host-header", "Values": ["api.doesnt-matter"]},
                        {"Field": "path-pattern", "Values": ["/*"]},
                    ],
                    Actions=[
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-10",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter-10", "Weight": 1}
                                ],
                                "TargetGroupStickiness": {"Enabled": False},
                            },
                        }
                    ],
                    Tags=[
                        {"Key": "application", "Value": "test-application"},
                        {"Key": "environment", "Value": input_args["environment"]},
                        {"Key": "service", "Value": "api"},
                        {"Key": "reason", "Value": "service"},
                        {"Key": "managed-by", "Value": "DBT Platform"},
                    ],
                ),
            ]
        )
    else:
        mock_boto_elbv2_client.delete_rule.assert_has_calls(
            [
                call(RuleArn="listener-rule-arn-doesnt-matter-8"),
                call(RuleArn="listener-rule-arn-doesnt-matter-9"),
                call(RuleArn="listener-rule-arn-doesnt-matter-10"),
            ]
        )


def test_alb_rules_create_with_rollback(
    fakefs,
    create_valid_platform_config_file,
    mock_application,
):
    load_application = Mock()
    load_application.return_value = mock_application
    mock_installed_version_provider = create_autospec(spec=InstalledVersionProvider, spec_set=True)
    mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(14, 0, 0)
    mock_config_validator = Mock(spec=ConfigValidator)
    mock_config_provider = ConfigProvider(
        mock_config_validator, installed_version_provider=mock_installed_version_provider
    )

    mock_session = mock_application.environments["test"].session

    lb_paginator = Mock()
    lb_paginator.paginate.return_value = [
        {
            "LoadBalancers": [
                {
                    "LoadBalancerArn": "alb-arn-doesnt-matter",
                },
            ],
            "NextMarker": "string",
        }
    ]

    listener_paginator = Mock()
    listener_paginator.paginate.return_value = [
        {
            "Listeners": [
                {
                    "ListenerArn": "listener-arn-doesnt-matter",
                    "LoadBalancerArn": "alb-arn-doesnt-matter",
                    "Port": 123,
                    "Protocol": "HTTPS",
                },
            ],
            "NextMarker": "string",
        }
    ]

    describe_rules_paginator = Mock()
    describe_rules_paginator.paginate.return_value = [
        {
            "Rules": [
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-1",
                    "Priority": "48000",
                    "Conditions": [
                        {
                            "Field": "path-pattern",
                            "Values": ["/secondary-service/*", "/secondary-service"],
                            "PathPatternConfig": {
                                "Values": ["/secondary-service/*", "/secondary-service"]
                            },
                        },
                        {
                            "Field": "host-header",
                            "Values": ["web.doesnt-matter"],
                            "HostHeaderConfig": {"Values": ["web.doesnt-matter"]},
                        },
                    ],
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-7",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter-1", "Weight": 1}
                                ],
                                "TargetGroupStickinessConfig": {"Enabled": False},
                            },
                        }
                    ],
                    "IsDefault": False,
                    "ResourceArn": "listener-rule-arn-doesnt-matter-1",
                },
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-2",
                    "Priority": "49000",
                    "Conditions": [
                        {
                            "Field": "path-pattern",
                            "Values": ["/*"],
                            "PathPatternConfig": {"Values": ["/*"]},
                        },
                        {
                            "Field": "host-header",
                            "Values": ["api.doesnt-matter"],
                            "HostHeaderConfig": {"Values": ["api.doesnt-matter"]},
                        },
                    ],
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-8",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter-8", "Weight": 1}
                                ],
                                "TargetGroupStickinessConfig": {"Enabled": False},
                            },
                        }
                    ],
                    "IsDefault": False,
                    "ResourceArn": "listener-rule-arn-doesnt-matter-2",
                },
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-3",
                    "Priority": "50000",
                    "Conditions": [
                        {
                            "Field": "path-pattern",
                            "Values": ["/*"],
                            "PathPatternConfig": {"Values": ["/*"]},
                        },
                        {
                            "Field": "host-header",
                            "Values": ["web.doesnt-matter"],
                            "HostHeaderConfig": {"Values": ["web.doesnt-matter"]},
                        },
                    ],
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-9",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter-9", "Weight": 1}
                                ],
                                "TargetGroupStickinessConfig": {"Enabled": False},
                            },
                        }
                    ],
                    "IsDefault": False,
                    "ResourceArn": "listener-rule-arn-doesnt-matter-3",
                },
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-4",
                    "Priority": "default",
                    "Conditions": [],
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter",
                            "Order": 1,
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter", "Weight": 1}
                                ],
                                "TargetGroupStickinessConfig": {"Enabled": False},
                            },
                        }
                    ],
                    "IsDefault": True,
                    "ResourceArn": "listener-rule-arn-doesnt-matter-4",
                },
            ],
            "NextMarker": "string",
        }
    ]

    describe_target_groups_paginator = Mock()
    # TODO set up tgs for each test environment
    describe_target_groups_paginator.paginate = Mock(
        side_effect=[
            [
                {
                    "TargetGroups": [
                        {
                            "TargetGroupArn": "tg-arn-doesnt-matter-2",
                            "TargetGroupName": "web-path-tg",
                            "Protocol": "HTTPS",
                            "Port": 443,
                            "VpcId": "vpc-xxxxxxxxx",
                            "HealthCheckProtocol": "HTTP",
                            "HealthCheckPort": "8080",
                            "HealthCheckEnabled": False,
                            "HealthCheckIntervalSeconds": 35,
                            "HealthCheckTimeoutSeconds": 30,
                            "HealthyThresholdCount": 3,
                            "UnhealthyThresholdCount": 3,
                            "HealthCheckPath": "/secondary-service",
                            "Matcher": {"HttpCode": "200,301,302"},
                            "LoadBalancerArns": ["alb-arn-doesnt-matter"],
                            "TargetType": "ip",
                            "ProtocolVersion": "HTTP1",
                            "IpAddressType": "ipv4",
                        },
                        {
                            "TargetGroupArn": "tg-arn-doesnt-matter-1",
                            "TargetGroupName": "web-tg-xxxxxx",
                            "Protocol": "HTTPS",
                            "Port": 443,
                            "VpcId": "vpc-xxxxxxxxx",
                            "HealthCheckProtocol": "HTTP",
                            "HealthCheckPort": "8080",
                            "HealthCheckEnabled": True,
                            "HealthCheckIntervalSeconds": 35,
                            "HealthCheckTimeoutSeconds": 30,
                            "HealthyThresholdCount": 3,
                            "UnhealthyThresholdCount": 3,
                            "HealthCheckPath": "/",
                            "Matcher": {"HttpCode": "200"},
                            "LoadBalancerArns": ["alb-arn-doesnt-matter"],
                            "TargetType": "ip",
                            "ProtocolVersion": "HTTP1",
                            "IpAddressType": "ipv4",
                        },
                        {
                            "TargetGroupArn": "tg-arn-doesnt-matter-3",
                            "TargetGroupName": "api-tg-yyyyy",
                            "Protocol": "HTTPS",
                            "Port": 443,
                            "VpcId": "vpc-xxxxxxxxx",
                            "HealthCheckProtocol": "HTTP",
                            "HealthCheckPort": "8080",
                            "HealthCheckEnabled": True,
                            "HealthCheckIntervalSeconds": 35,
                            "HealthCheckTimeoutSeconds": 30,
                            "HealthyThresholdCount": 3,
                            "UnhealthyThresholdCount": 3,
                            "HealthCheckPath": "/",
                            "Matcher": {"HttpCode": "200"},
                            "LoadBalancerArns": ["alb-arn-doesnt-matter"],
                            "TargetType": "ip",
                            "ProtocolVersion": "HTTP1",
                            "IpAddressType": "ipv4",
                        },
                        {
                            "TargetGroupArn": "tg-arn-doesnt-matter-7",
                            "TargetGroupName": "web-path-tg",
                            "Protocol": "HTTPS",
                            "Port": 443,
                            "VpcId": "vpc-xxxxxxxxx",
                            "HealthCheckProtocol": "HTTP",
                            "HealthCheckPort": "8080",
                            "HealthCheckEnabled": False,
                            "HealthCheckIntervalSeconds": 35,
                            "HealthCheckTimeoutSeconds": 30,
                            "HealthyThresholdCount": 3,
                            "UnhealthyThresholdCount": 3,
                            "HealthCheckPath": "/secondary-service",
                            "Matcher": {"HttpCode": "200,301,302"},
                            "LoadBalancerArns": ["alb-arn-doesnt-matter"],
                            "TargetType": "ip",
                            "ProtocolVersion": "HTTP1",
                            "IpAddressType": "ipv4",
                        },
                        {
                            "TargetGroupArn": "tg-arn-doesnt-matter-9",
                            "TargetGroupName": "web-tg-xxxxxx",
                            "Protocol": "HTTPS",
                            "Port": 443,
                            "VpcId": "vpc-xxxxxxxxx",
                            "HealthCheckProtocol": "HTTP",
                            "HealthCheckPort": "8080",
                            "HealthCheckEnabled": True,
                            "HealthCheckIntervalSeconds": 35,
                            "HealthCheckTimeoutSeconds": 30,
                            "HealthyThresholdCount": 3,
                            "UnhealthyThresholdCount": 3,
                            "HealthCheckPath": "/",
                            "Matcher": {"HttpCode": "200"},
                            "LoadBalancerArns": ["alb-arn-doesnt-matter"],
                            "TargetType": "ip",
                            "ProtocolVersion": "HTTP1",
                            "IpAddressType": "ipv4",
                        },
                        {
                            "TargetGroupArn": "tg-arn-doesnt-matter-8",
                            "TargetGroupName": "api-tg-yyyyy",
                            "Protocol": "HTTPS",
                            "Port": 443,
                            "VpcId": "vpc-xxxxxxxxx",
                            "HealthCheckProtocol": "HTTP",
                            "HealthCheckPort": "8080",
                            "HealthCheckEnabled": True,
                            "HealthCheckIntervalSeconds": 35,
                            "HealthCheckTimeoutSeconds": 30,
                            "HealthyThresholdCount": 3,
                            "UnhealthyThresholdCount": 3,
                            "HealthCheckPath": "/",
                            "Matcher": {"HttpCode": "200"},
                            "LoadBalancerArns": ["alb-arn-doesnt-matter"],
                            "TargetType": "ip",
                            "ProtocolVersion": "HTTP1",
                            "IpAddressType": "ipv4",
                        },
                    ],
                    "NextMarker": "string",
                },
            ],
            [
                {
                    "TargetGroups": [
                        {
                            "TargetGroupArn": "tg-arn-doesnt-matter-7",
                            "TargetGroupName": "web-path-tg",
                            "Protocol": "HTTPS",
                            "Port": 443,
                            "VpcId": "vpc-xxxxxxxxx",
                            "HealthCheckProtocol": "HTTP",
                            "HealthCheckPort": "8080",
                            "HealthCheckEnabled": False,
                            "HealthCheckIntervalSeconds": 35,
                            "HealthCheckTimeoutSeconds": 30,
                            "HealthyThresholdCount": 3,
                            "UnhealthyThresholdCount": 3,
                            "HealthCheckPath": "/secondary-service",
                            "Matcher": {"HttpCode": "200,301,302"},
                            "LoadBalancerArns": ["alb-arn-doesnt-matter"],
                            "TargetType": "ip",
                            "ProtocolVersion": "HTTP1",
                            "IpAddressType": "ipv4",
                        },
                    ],
                    "NextMarker": "string",
                }
            ],
            [
                {
                    "TargetGroups": [
                        {
                            "TargetGroupArn": "tg-arn-doesnt-matter-8",
                            "TargetGroupName": "api-tg-yyyyy",
                            "Protocol": "HTTPS",
                            "Port": 443,
                            "VpcId": "vpc-xxxxxxxxx",
                            "HealthCheckProtocol": "HTTP",
                            "HealthCheckPort": "8080",
                            "HealthCheckEnabled": True,
                            "HealthCheckIntervalSeconds": 35,
                            "HealthCheckTimeoutSeconds": 30,
                            "HealthyThresholdCount": 3,
                            "UnhealthyThresholdCount": 3,
                            "HealthCheckPath": "/",
                            "Matcher": {"HttpCode": "200"},
                            "LoadBalancerArns": ["alb-arn-doesnt-matter"],
                            "TargetType": "ip",
                            "ProtocolVersion": "HTTP1",
                            "IpAddressType": "ipv4",
                        },
                    ],
                    "NextMarker": "string",
                }
            ],
            [
                {
                    "TargetGroups": [
                        {
                            "TargetGroupArn": "tg-arn-doesnt-matter-9",
                            "TargetGroupName": "web-tg-xxxxxx",
                            "Protocol": "HTTPS",
                            "Port": 443,
                            "VpcId": "vpc-xxxxxxxxx",
                            "HealthCheckProtocol": "HTTP",
                            "HealthCheckPort": "8080",
                            "HealthCheckEnabled": True,
                            "HealthCheckIntervalSeconds": 35,
                            "HealthCheckTimeoutSeconds": 30,
                            "HealthyThresholdCount": 3,
                            "UnhealthyThresholdCount": 3,
                            "HealthCheckPath": "/",
                            "Matcher": {"HttpCode": "200"},
                            "LoadBalancerArns": ["alb-arn-doesnt-matter"],
                            "TargetType": "ip",
                            "ProtocolVersion": "HTTP1",
                            "IpAddressType": "ipv4",
                        },
                    ],
                    "NextMarker": "string",
                }
            ],
        ]
    )

    mock_boto_elbv2_client = Mock(name="client-mock")
    mock_boto_elbv2_client.get_paginator.side_effect = lambda op: {
        "describe_load_balancers": lb_paginator,
        "describe_listeners": listener_paginator,
        "describe_rules": describe_rules_paginator,
        "describe_target_groups": describe_target_groups_paginator,
    }.get(op, Mock())

    mock_boto_elbv2_client.describe_tags = Mock(
        side_effect=[
            {
                "TagDescriptions": [
                    {
                        "ResourceArn": "alb-arn-doesnt-matter",
                        "Tags": [
                            {"Key": "copilot-application", "Value": "test-application"},
                            {"Key": "copilot-environment", "Value": "test"},
                        ],
                    },
                ]
            },
            {
                "TagDescriptions": [
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-1",
                        "Tags": [],
                    },
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-2",
                        "Tags": [],
                    },
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-3",
                        "Tags": [],
                    },
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-4",
                        "Tags": [],
                    },
                ]
            },
            {
                "TagDescriptions": [
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-1",
                        "Tags": [
                            {"Key": "environment", "Value": "test"},
                            {"Key": "application", "Value": "test-application"},
                            {"Key": "managed-by", "Value": "DBT Platform - Service Terraform"},
                            {"Key": "service", "Value": "web"},
                        ],
                    },
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-2",
                        "Tags": [
                            {"Key": "environment", "Value": "test"},
                            {"Key": "application", "Value": "test-application"},
                            {"Key": "managed-by", "Value": "DBT Platform - Service Terraform"},
                            {"Key": "service", "Value": "web-path"},
                        ],
                    },
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-3",
                        "Tags": [
                            {"Key": "environment", "Value": "test"},
                            {"Key": "application", "Value": "test-application"},
                            {"Key": "managed-by", "Value": "DBT Platform - Service Terraform"},
                            {"Key": "service", "Value": "api"},
                        ],
                    },
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-7",
                        "Tags": [
                            {"Key": "copilot-application", "Value": "test-application"},
                            {"Key": "copilot-environment", "Value": "test"},
                            {"Key": "copilot-service", "Value": "web-path"},
                        ],
                    },
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-8",
                        "Tags": [
                            {"Key": "copilot-application", "Value": "test-application"},
                            {"Key": "copilot-environment", "Value": "test"},
                            {"Key": "copilot-service", "Value": "api"},
                        ],
                    },
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-9",
                        "Tags": [
                            {"Key": "copilot-application", "Value": "test-application"},
                            {"Key": "copilot-environment", "Value": "test"},
                            {"Key": "copilot-service", "Value": "web"},
                        ],
                    },
                ]
            },
            {
                "TagDescriptions": [
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-7",
                        "Tags": [
                            {"Key": "copilot-application", "Value": "test-application"},
                            {"Key": "copilot-environment", "Value": "test"},
                            {"Key": "copilot-service", "Value": "web-path"},
                        ],
                    },
                ]
            },
            {
                "TagDescriptions": [
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-8",
                        "Tags": [
                            {"Key": "copilot-application", "Value": "test-application"},
                            {"Key": "copilot-environment", "Value": "test"},
                            {"Key": "copilot-service", "Value": "api"},
                        ],
                    },
                ]
            },
            {
                "TagDescriptions": [
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-9",
                        "Tags": [
                            {"Key": "copilot-application", "Value": "test-application"},
                            {"Key": "copilot-environment", "Value": "test"},
                            {"Key": "copilot-service", "Value": "web"},
                        ],
                    },
                ]
            },
        ]
    )

    mock_boto_elbv2_client.create_rule = Mock(
        side_effect=[
            {"Rules": [{"RuleArn": "platform-new-web-path-arn"}]},
            ClientError(
                {"Error": {"Code": "ValidationError", "Message": "Simulated failure"}},
                "CreateRule",
            ),
        ]
    )

    mock_boto_elbv2_client.delete_rule = Mock(
        side_effect=[
            {"Rules": [{"RuleArn": "platform-new-web-path-arn"}]},
        ]
    )

    mock_session = Mock(name="session-mock")
    mock_session.client.return_value = mock_boto_elbv2_client

    mock_io = MagicMock()

    update_aws = UpdateALBRules(
        mock_session,
        config_provider=mock_config_provider,
        io=mock_io,
        load_application=load_application,
    )

    with pytest.raises(
        PlatformException,
        match="""Rolledback rules by creating: \[\] \n and deleting \['platform-new-web-path-arn'\]""",
    ):
        update_aws.update_alb_rules(
            environment="test",
        )

    mock_io.info.assert_has_calls(
        [
            call("Deployment Mode: dual-deploy-platform-traffic"),
            call("ARN: listener-arn-doesnt-matter"),
            call(
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-1"
            ),
            call("Updated forward action for service web-path to use: tg-arn-doesnt-matter-2"),
            call(
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-2"
            ),
            call("Updated forward action for service api to use: tg-arn-doesnt-matter-3"),
            call(
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-3"
            ),
            call("Updated forward action for service web to use: tg-arn-doesnt-matter-1"),
            call(
                "Creating platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-1"
            ),
            call(
                "Creating platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-3"
            ),
            call("Attempting to rollback changes ..."),
            call("Rollback completed successfully"),
        ]
    )

    mock_boto_elbv2_client.create_rule.assert_has_calls(
        [
            call(
                ListenerArn="listener-arn-doesnt-matter",
                Priority=10000,
                Conditions=[
                    {
                        "Field": "path-pattern",
                        "Values": ["/secondary-service/*", "/secondary-service"],
                    },
                    {"Field": "host-header", "Values": ["web.doesnt-matter"]},
                ],
                Actions=[
                    {
                        "Type": "forward",
                        "TargetGroupArn": "tg-arn-doesnt-matter-2",
                        "ForwardConfig": {
                            "TargetGroups": [
                                {"TargetGroupArn": "tg-arn-doesnt-matter-2", "Weight": 1}
                            ],
                            "TargetGroupStickinessConfig": {"Enabled": False},
                        },
                    }
                ],
                Tags=[
                    {"Key": "application", "Value": "test-application"},
                    {"Key": "environment", "Value": "test"},
                    {"Key": "service", "Value": "web-path"},
                    {"Key": "reason", "Value": "service"},
                    {"Key": "managed-by", "Value": "DBT Platform"},
                ],
            ),
            call(
                ListenerArn="listener-arn-doesnt-matter",
                Priority=10100,
                Conditions=[
                    {"Field": "path-pattern", "Values": ["/*"]},
                    {"Field": "host-header", "Values": ["web.doesnt-matter"]},
                ],
                Actions=[
                    {
                        "Type": "forward",
                        "TargetGroupArn": "tg-arn-doesnt-matter-1",
                        "ForwardConfig": {
                            "TargetGroups": [
                                {"TargetGroupArn": "tg-arn-doesnt-matter-1", "Weight": 1}
                            ],
                            "TargetGroupStickinessConfig": {"Enabled": False},
                        },
                    }
                ],
                Tags=[
                    {"Key": "application", "Value": "test-application"},
                    {"Key": "environment", "Value": "test"},
                    {"Key": "service", "Value": "web"},
                    {"Key": "reason", "Value": "service"},
                    {"Key": "managed-by", "Value": "DBT Platform"},
                ],
            ),
        ]
    )

    mock_boto_elbv2_client.delete_rule.assert_has_calls(
        [
            call(RuleArn="platform-new-web-path-arn"),
        ]
    )


def test_alb_rules_delete_with_rollback(
    fakefs,
    create_valid_platform_config_file,
    mock_application,
):
    load_application = Mock()
    load_application.return_value = mock_application
    mock_installed_version_provider = create_autospec(spec=InstalledVersionProvider, spec_set=True)
    mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(14, 0, 0)
    mock_config_validator = Mock(spec=ConfigValidator)
    mock_config_provider = ConfigProvider(
        mock_config_validator, installed_version_provider=mock_installed_version_provider
    )

    mock_session = mock_application.environments["production"].session

    lb_paginator = Mock()
    lb_paginator.paginate.return_value = [
        {
            "LoadBalancers": [
                {
                    "LoadBalancerArn": "alb-arn-doesnt-matter",
                },
            ],
            "NextMarker": "string",
        }
    ]

    listener_paginator = Mock()
    listener_paginator.paginate.return_value = [
        {
            "Listeners": [
                {
                    "ListenerArn": "listener-arn-doesnt-matter",
                    "LoadBalancerArn": "alb-arn-doesnt-matter",
                    "Port": 123,
                    "Protocol": "HTTPS",
                },
            ],
            "NextMarker": "string",
        }
    ]

    describe_rules_paginator = Mock()
    describe_rules_paginator.paginate.return_value = [
        {
            "Rules": [
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-8",
                    "Priority": "10000",
                    "Conditions": [
                        {
                            "Field": "path-pattern",
                            "Values": ["/secondary-service/*", "/secondary-service"],
                            "PathPatternConfig": {
                                "Values": ["/secondary-service/*", "/secondary-service"]
                            },
                        },
                        {
                            "Field": "host-header",
                            "Values": ["web.doesnt-matter"],
                            "HostHeaderConfig": {"Values": ["web.doesnt-matter"]},
                        },
                    ],
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-2",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter-2", "Weight": 1}
                                ],
                                "TargetGroupStickinessConfig": {"Enabled": False},
                            },
                        }
                    ],
                    "IsDefault": False,
                    "ResourceArn": "listener-rule-arn-doesnt-matter-8",
                },
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-9",
                    "Priority": "10100",
                    "Conditions": [
                        {
                            "Field": "path-pattern",
                            "Values": ["/*"],
                            "PathPatternConfig": {"Values": ["/*"]},
                        },
                        {
                            "Field": "host-header",
                            "Values": ["web.doesnt-matter"],
                            "HostHeaderConfig": {"Values": ["web.doesnt-matter"]},
                        },
                    ],
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-1",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter-1", "Weight": 1}
                                ],
                                "TargetGroupStickinessConfig": {"Enabled": False},
                            },
                        }
                    ],
                    "IsDefault": False,
                    "ResourceArn": "listener-rule-arn-doesnt-matter-9",
                },
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-10",
                    "Priority": "11000",
                    "Conditions": [
                        {
                            "Field": "path-pattern",
                            "Values": ["/*"],
                            "PathPatternConfig": {"Values": ["/*"]},
                        },
                        {
                            "Field": "host-header",
                            "Values": ["api.doesnt-matter"],
                            "HostHeaderConfig": {"Values": ["api.doesnt-matter"]},
                        },
                    ],
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-3",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter-3", "Weight": 1}
                                ],
                                "TargetGroupStickinessConfig": {"Enabled": False},
                            },
                        }
                    ],
                    "IsDefault": False,
                    "ResourceArn": "listener-rule-arn-doesnt-matter-10",
                },
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-1",
                    "Priority": "48000",
                    "Conditions": [
                        {
                            "Field": "path-pattern",
                            "Values": ["/secondary-service/*", "/secondary-service"],
                            "PathPatternConfig": {
                                "Values": ["/secondary-service/*", "/secondary-service"]
                            },
                        },
                        {
                            "Field": "host-header",
                            "Values": ["web.doesnt-matter"],
                            "HostHeaderConfig": {"Values": ["web.doesnt-matter"]},
                        },
                    ],
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-7",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter-1", "Weight": 1}
                                ],
                                "TargetGroupStickinessConfig": {"Enabled": False},
                            },
                        }
                    ],
                    "IsDefault": False,
                    "ResourceArn": "listener-rule-arn-doesnt-matter-1",
                },
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-2",
                    "Priority": "49000",
                    "Conditions": [
                        {
                            "Field": "path-pattern",
                            "Values": ["/*"],
                            "PathPatternConfig": {"Values": ["/*"]},
                        },
                        {
                            "Field": "host-header",
                            "Values": ["api.doesnt-matter"],
                            "HostHeaderConfig": {"Values": ["api.doesnt-matter"]},
                        },
                    ],
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-8",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter-8", "Weight": 1}
                                ],
                                "TargetGroupStickinessConfig": {"Enabled": False},
                            },
                        }
                    ],
                    "IsDefault": False,
                    "ResourceArn": "listener-rule-arn-doesnt-matter-2",
                },
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-3",
                    "Priority": "50000",
                    "Conditions": [
                        {
                            "Field": "path-pattern",
                            "Values": ["/*"],
                            "PathPatternConfig": {"Values": ["/*"]},
                        },
                        {
                            "Field": "host-header",
                            "Values": ["web.doesnt-matter"],
                            "HostHeaderConfig": {"Values": ["web.doesnt-matter"]},
                        },
                    ],
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-9",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter-9", "Weight": 1}
                                ],
                                "TargetGroupStickinessConfig": {"Enabled": False},
                            },
                        }
                    ],
                    "IsDefault": False,
                    "ResourceArn": "listener-rule-arn-doesnt-matter-3",
                },
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-4",
                    "Priority": "default",
                    "Conditions": [],
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter",
                            "Order": 1,
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter", "Weight": 1}
                                ],
                                "TargetGroupStickinessConfig": {"Enabled": False},
                            },
                        }
                    ],
                    "IsDefault": True,
                    "ResourceArn": "listener-rule-arn-doesnt-matter-4",
                },
            ],
            "NextMarker": "string",
        }
    ]

    mock_boto_elbv2_client = Mock(name="client-mock")
    mock_boto_elbv2_client.get_paginator.side_effect = lambda op: {
        "describe_load_balancers": lb_paginator,
        "describe_listeners": listener_paginator,
        "describe_rules": describe_rules_paginator,
    }.get(op, Mock())

    mock_boto_elbv2_client.describe_tags = Mock(
        side_effect=[
            {
                "TagDescriptions": [
                    {
                        "ResourceArn": "alb-arn-doesnt-matter",
                        "Tags": [
                            {"Key": "copilot-application", "Value": "test-application"},
                            {"Key": "copilot-environment", "Value": "production"},
                        ],
                    },
                ]
            },
            {
                "TagDescriptions": [
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-8",
                        "Tags": [
                            {"Key": "application", "Value": "test-application"},
                            {"Key": "environment", "Value": "production"},
                            {"Key": "service", "Value": "web-path"},
                            {"Key": "reason", "Value": "service"},
                            {"Key": "managed-by", "Value": "DBT Platform"},
                        ],
                    },
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-9",
                        "Tags": [
                            {"Key": "application", "Value": "test-application"},
                            {"Key": "environment", "Value": "production"},
                            {"Key": "service", "Value": "web"},
                            {"Key": "reason", "Value": "service"},
                            {"Key": "managed-by", "Value": "DBT Platform"},
                        ],
                    },
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-10",
                        "Tags": [
                            {"Key": "application", "Value": "test-application"},
                            {"Key": "environment", "Value": "production"},
                            {"Key": "service", "Value": "api"},
                            {"Key": "reason", "Value": "service"},
                            {"Key": "managed-by", "Value": "DBT Platform"},
                        ],
                    },
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-1",
                        "Tags": [],
                    },
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-2",
                        "Tags": [],
                    },
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-3",
                        "Tags": [],
                    },
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-4",
                        "Tags": [],
                    },
                ]
            },
        ]
    )

    mock_boto_elbv2_client.delete_rule = Mock(
        side_effect=[
            {"Rules": [{"RuleArn": "listener-rule-arn-doesnt-matter-8"}]},
            ClientError(
                {"Error": {"Code": "ValidationError", "Message": "Simulated failure"}},
                "CreateRule",
            ),
        ]
    )

    mock_boto_elbv2_client.create_rule = Mock(
        side_effect=[
            {"Rules": [{"RuleArn": "listener-rule-arn-doesnt-matter-8"}]},
        ]
    )

    mock_session = Mock(name="session-mock")
    mock_session.client.return_value = mock_boto_elbv2_client

    mock_io = MagicMock()

    update_aws = UpdateALBRules(
        mock_session,
        config_provider=mock_config_provider,
        io=mock_io,
        load_application=load_application,
    )

    with pytest.raises(
        PlatformException,
        match="""Rolledback rules by creating: \['listener-rule-arn-doesnt-matter-8'\] \n and deleting \[\]""",
    ):
        update_aws.update_alb_rules(
            environment="production",
        )

    mock_io.info.assert_has_calls(
        [
            call("Deployment Mode: copilot"),
            call("ARN: listener-arn-doesnt-matter"),
            call("Deleted existing rule: listener-rule-arn-doesnt-matter-8"),
            call("Attempting to rollback changes ..."),
            call("Rollback completed successfully"),
        ]
    )

    mock_boto_elbv2_client.create_rule.assert_has_calls(
        [
            call(
                ListenerArn="listener-arn-doesnt-matter",
                Priority="10000",
                Conditions=[
                    {
                        "Field": "path-pattern",
                        "Values": ["/secondary-service/*", "/secondary-service"],
                    },
                    {"Field": "host-header", "Values": ["web.doesnt-matter"]},
                ],
                Actions=[
                    {
                        "Type": "forward",
                        "TargetGroupArn": "tg-arn-doesnt-matter-2",
                        "ForwardConfig": {
                            "TargetGroups": [
                                {"TargetGroupArn": "tg-arn-doesnt-matter-2", "Weight": 1}
                            ],
                            "TargetGroupStickinessConfig": {"Enabled": False},
                        },
                    }
                ],
                Tags=[
                    {"Key": "application", "Value": "test-application"},
                    {"Key": "environment", "Value": "production"},
                    {"Key": "service", "Value": "web-path"},
                    {"Key": "reason", "Value": "service"},
                    {"Key": "managed-by", "Value": "DBT Platform"},
                ],
            )
        ]
    )

    mock_boto_elbv2_client.delete_rule.assert_has_calls(
        [
            call(RuleArn="listener-rule-arn-doesnt-matter-8"),
            call(RuleArn="listener-rule-arn-doesnt-matter-9"),
        ]
    )


def test_alb_rules_with_manual(
    fakefs,
    create_valid_platform_config_file,
    mock_application,
):

    load_application = Mock()
    load_application.return_value = mock_application
    mock_installed_version_provider = create_autospec(spec=InstalledVersionProvider, spec_set=True)
    mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(14, 0, 0)
    mock_config_validator = Mock(spec=ConfigValidator)
    mock_config_provider = ConfigProvider(
        mock_config_validator, installed_version_provider=mock_installed_version_provider
    )

    mock_session = mock_application.environments["test"].session

    lb_paginator = Mock()
    lb_paginator.paginate.return_value = [
        {
            "LoadBalancers": [
                {
                    "LoadBalancerArn": "alb-arn-doesnt-matter",
                },
            ],
            "NextMarker": "string",
        }
    ]

    listener_paginator = Mock()
    listener_paginator.paginate.return_value = [
        {
            "Listeners": [
                {
                    "ListenerArn": "listener-arn-doesnt-matter",
                    "LoadBalancerArn": "alb-arn-doesnt-matter",
                    "Port": 123,
                    "Protocol": "HTTPS",
                },
            ],
            "NextMarker": "string",
        }
    ]

    describe_rules_paginator = Mock()
    describe_rules_paginator.paginate.return_value = [
        {
            "Rules": [
                {
                    "RuleArn": "listener-rule-arn-manual",
                    "Priority": "10000",
                    "Conditions": [
                        {
                            "Field": "path-pattern",
                            "Values": ["/*"],
                            "PathPatternConfig": {"Values": ["/*"]},
                        },
                        {
                            "Field": "host-header",
                            "Values": ["api.doesnt-matter"],
                            "HostHeaderConfig": {"Values": ["api.doesnt-matter"]},
                        },
                    ],
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-8",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter-8", "Weight": 1}
                                ],
                                "TargetGroupStickinessConfig": {"Enabled": False},
                            },
                        }
                    ],
                    "IsDefault": False,
                    "ResourceArn": "listener-rule-arn-doesnt-matter-2",
                },
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-3",
                    "Priority": "50000",
                    "Conditions": [
                        {
                            "Field": "path-pattern",
                            "Values": ["/*"],
                            "PathPatternConfig": {"Values": ["/*"]},
                        },
                        {
                            "Field": "host-header",
                            "Values": ["web.doesnt-matter"],
                            "HostHeaderConfig": {"Values": ["web.doesnt-matter"]},
                        },
                    ],
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-9",
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter-9", "Weight": 1}
                                ],
                                "TargetGroupStickinessConfig": {"Enabled": False},
                            },
                        }
                    ],
                    "IsDefault": False,
                    "ResourceArn": "listener-rule-arn-doesnt-matter-3",
                },
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-4",
                    "Priority": "default",
                    "Conditions": [],
                    "Actions": [
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter",
                            "Order": 1,
                            "ForwardConfig": {
                                "TargetGroups": [
                                    {"TargetGroupArn": "tg-arn-doesnt-matter", "Weight": 1}
                                ],
                                "TargetGroupStickinessConfig": {"Enabled": False},
                            },
                        }
                    ],
                    "IsDefault": True,
                    "ResourceArn": "listener-rule-arn-doesnt-matter-4",
                },
            ],
            "NextMarker": "string",
        }
    ]
    mock_boto_elbv2_client = Mock(name="client-mock")
    mock_boto_elbv2_client.get_paginator.side_effect = lambda op: {
        "describe_load_balancers": lb_paginator,
        "describe_listeners": listener_paginator,
        "describe_rules": describe_rules_paginator,
    }.get(op, Mock())

    mock_boto_elbv2_client.describe_tags = Mock(
        side_effect=[
            {
                "TagDescriptions": [
                    {
                        "ResourceArn": "alb-arn-doesnt-matter",
                        "Tags": [
                            {"Key": "copilot-application", "Value": "test-application"},
                            {"Key": "copilot-environment", "Value": "test"},
                        ],
                    },
                ]
            },
            {
                "TagDescriptions": [
                    {
                        "ResourceArn": "listener-rule-arn-manual",
                        "Tags": [],
                    },
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-3",
                        "Tags": [],
                    },
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-4",
                        "Tags": [],
                    },
                ]
            },
        ]
    )

    mock_session = Mock(name="session-mock")
    mock_session.client.return_value = mock_boto_elbv2_client

    mock_io = MagicMock()

    update_aws = UpdateALBRules(
        mock_session,
        config_provider=mock_config_provider,
        io=mock_io,
        load_application=load_application,
    )

    with pytest.raises(
        PlatformException,
        match="""The following rules have been created manually please review and if required set \n            the rules priority to the copilot range after priority: 48000.\n\n            Rules: \['listener-rule-arn-manual'\]""",
    ):
        update_aws.update_alb_rules(
            environment="test",
        )
