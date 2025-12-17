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

    def __init__(self, environment, create_platform_rules=False, manual_rule=False):
        self.environment = environment
        self.create_platform_rules = create_platform_rules
        self.manual_rule = manual_rule
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
                        "LoadBalancerArn": "copilot-alb-arn",
                    },
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
            # Dummy rule
            self.fixtures.create_rule_response(12, "1000", http_headers=["forward"]),
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
        if self.manual_rule:
            rules.append(
                self.fixtures.create_rule_response(
                    11,
                    "9000",
                )
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

        target_rules = [
            self.fixtures.create_target_group(4, "/secondary-service"),
            self.fixtures.create_target_group(5),
            self.fixtures.create_target_group(6),
            self.fixtures.create_target_group(7, "/doesnt-matter"),
            self.fixtures.create_target_group(8, "/secondary-service"),
            self.fixtures.create_target_group(9),
            self.fixtures.create_target_group(10),
            # Dummy tg
            self.fixtures.create_target_group(12),
        ]
        if self.manual_rule:
            target_rules.append(
                self.fixtures.create_target_group(
                    11,
                )
            )
        paginator.paginate = Mock(
            side_effect=[
                [
                    {
                        "TargetGroups": target_rules,
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

        rule_tags = []
        if self.create_platform_rules:
            rule_tags.extend(
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

        if self.manual_rule:
            rule_tags.append(
                self.fixtures.create_tag_descriptions(
                    "listener-rule-arn-doesnt-matter-11",
                )
            )
        return Mock(
            side_effect=[
                {  # ALB
                    "TagDescriptions": [
                        self.fixtures.create_tag_descriptions(
                            "copilot-alb-arn",
                            {
                                "copilot-application": "test-application",
                                "copilot-environment": self.environment,
                            },
                        ),
                        self.fixtures.create_tag_descriptions(
                            "alb-arn-doesnt-matter",
                            {
                                "copilot-application": "test-application",
                                "copilot-environment": self.environment,
                                "application": "test-application",
                                "environment": self.environment,
                                "managed-by": "DBT Platform - Terraform",
                            },
                        ),
                    ]
                },
                {  # Listener rule tags
                    "TagDescriptions": [
                        self.fixtures.create_tag_descriptions(
                            "listener-rule-arn-doesnt-matter-1",
                            {
                                "name": "AllowedIps",
                                "service": "web",
                                "reason": "MaintenancePage",
                            },
                        ),
                        self.fixtures.create_tag_descriptions(
                            "listener-rule-arn-doesnt-matter-2",
                            {
                                "name": "AllowedSourceIps",
                                "service": "web",
                                "reason": "MaintenancePage",
                            },
                        ),
                        self.fixtures.create_tag_descriptions(
                            "listener-rule-arn-doesnt-matter-3",
                            {
                                "name": "BypassIpFilter",
                                "service": "web",
                                "reason": "MaintenancePage",
                            },
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
                        # Dummy Rule tags
                        self.fixtures.create_tag_descriptions(
                            "listener-rule-arn-doesnt-matter-12",
                            {
                                "application": "test-application",
                                "service": "web",
                                "reason": "DummyRule",
                                "managed-by": "DBT Platform - Service Terraform",
                                "environment": self.environment,
                            },
                        ),
                        *rule_tags,
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
                        self.fixtures.create_tag_descriptions(
                            "tg-arn-doesnt-matter-12",
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
    "input_args, expected_logs, create_platform_rules, assert_created_rules, assert_deleted_rules",
    [
        (
            {
                "environment": "production",
            },
            {
                "info": [
                    "Deployment Mode: copilot",
                    "ARN: listener-rule-arn-doesnt-matter-8",
                    "Priority: 10000",
                    "Hosts: web.doesnt-matter",
                    "Paths: /secondary-service/*,/secondary-service\n",
                    "ARN: listener-rule-arn-doesnt-matter-9",
                    "Priority: 10100",
                    "Hosts: web.doesnt-matter",
                    "Paths: /*\n",
                    "ARN: listener-rule-arn-doesnt-matter-10",
                    "Priority: 11000",
                    "Hosts: api.doesnt-matter",
                    "Paths: /*\n",
                    "Deleted rules: 3",
                    "ARN: listener-rule-arn-doesnt-matter-8",
                    "Priority: 10000",
                    "Hosts: web.doesnt-matter",
                    "Paths: /secondary-service/*,/secondary-service\n",
                    "ARN: listener-rule-arn-doesnt-matter-9",
                    "Priority: 10100",
                    "Hosts: web.doesnt-matter",
                    "Paths: /*\n",
                    "ARN: listener-rule-arn-doesnt-matter-10",
                    "Priority: 11000",
                    "Hosts: api.doesnt-matter",
                    "Paths: /*\n",
                ],
                "warn": ["Platform rules will be deleted"],
                "debug": [
                    "Load Balancer ARN: alb-arn-doesnt-matter",
                    "Listener ARN: listener-arn-doesnt-matter",
                    "Deleted existing rule: listener-rule-arn-doesnt-matter-8",
                    "Deleted existing rule: listener-rule-arn-doesnt-matter-9",
                    "Deleted existing rule: listener-rule-arn-doesnt-matter-10",
                ],
            },
            True,
            False,
            True,
        ),
        (
            {
                "environment": "development",
            },
            {
                "info": [
                    "Deployment Mode: dual-deploy-copilot-traffic",
                    "ARN: listener-rule-arn-doesnt-matter-8",
                    "Priority: 10000",
                    "Hosts: web.doesnt-matter",
                    "Paths: /secondary-service/*,/secondary-service\n",
                    "ARN: listener-rule-arn-doesnt-matter-9",
                    "Priority: 10100",
                    "Hosts: web.doesnt-matter",
                    "Paths: /*\n",
                    "ARN: listener-rule-arn-doesnt-matter-10",
                    "Priority: 11000",
                    "Hosts: api.doesnt-matter",
                    "Paths: /*\n",
                    "Deleted rules: 3",
                    "ARN: listener-rule-arn-doesnt-matter-8",
                    "Priority: 10000",
                    "Hosts: web.doesnt-matter",
                    "Paths: /secondary-service/*,/secondary-service\n",
                    "ARN: listener-rule-arn-doesnt-matter-9",
                    "Priority: 10100",
                    "Hosts: web.doesnt-matter",
                    "Paths: /*\n",
                    "ARN: listener-rule-arn-doesnt-matter-10",
                    "Priority: 11000",
                    "Hosts: api.doesnt-matter",
                    "Paths: /*\n",
                ],
                "warn": ["Platform rules will be deleted"],
                "debug": [
                    "Load Balancer ARN: alb-arn-doesnt-matter",
                    "Listener ARN: listener-arn-doesnt-matter",
                    "Deleted existing rule: listener-rule-arn-doesnt-matter-8",
                    "Deleted existing rule: listener-rule-arn-doesnt-matter-9",
                    "Deleted existing rule: listener-rule-arn-doesnt-matter-10",
                ],
            },
            True,
            False,
            True,
        ),
        (
            {
                "environment": "test",
            },
            {
                "info": [
                    "Deployment Mode: dual-deploy-platform-traffic",
                    "Created rules: 2",
                    "ARN: platform-new-web-arn",
                    "Priority: 10000",
                    "Hosts: web.dev.test-app.uktrade.digital",
                    "Paths: /*\n",
                    "ARN: platform-new-api-arn",
                    "Priority: 11000",
                    "Hosts: api.dev.test-app.uktrade.digital",
                    "Paths: /*\n",
                ],
                "debug": [
                    "Load Balancer ARN: alb-arn-doesnt-matter",
                    "Listener ARN: listener-arn-doesnt-matter",
                ],
            },
            False,
            True,
            False,
        ),
        (
            {
                "environment": "staging",
            },
            {
                "info": [
                    "Deployment Mode: platform",
                    "Created rules: 2",
                    "ARN: platform-new-web-arn",
                    "Priority: 10000",
                    "Hosts: web.dev.test-app.uktrade.digital",
                    "Paths: /*\n",
                    "ARN: platform-new-api-arn",
                    "Priority: 11000",
                    "Hosts: api.dev.test-app.uktrade.digital",
                    "Paths: /*\n",
                    "Deleted rules: 1",
                    "ARN: listener-rule-arn-doesnt-matter-12",
                    "Priority: 1000",
                    "Hosts: web.doesnt-matter",
                    "Paths: /*\n",
                ],
                "debug": [
                    "Load Balancer ARN: alb-arn-doesnt-matter",
                    "Listener ARN: listener-arn-doesnt-matter",
                    "Deleted existing rule: listener-rule-arn-doesnt-matter-12",
                ],
            },
            False,
            True,
            False,
        ),
    ],
)
def test_alb_rules(
    fakefs,
    create_valid_platform_config_file,
    create_valid_multiple_service_config_files,
    mock_application,
    input_args,
    expected_logs,
    create_platform_rules,
    assert_created_rules,
    assert_deleted_rules,
):

    load_application = Mock()
    load_application.return_value = mock_application
    mock_installed_version_provider = create_autospec(spec=InstalledVersionProvider, spec_set=True)
    mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(14, 0, 0)
    mock_config_validator = Mock(spec=ConfigValidator)
    mock_config_provider = ConfigProvider(
        mock_config_validator, installed_version_provider=mock_installed_version_provider
    )

    mock_alb = MockALBService(
        environment=input_args["environment"], create_platform_rules=create_platform_rules
    )
    mock_boto_elbv2_client = mock_alb.create_elbv2_client_mock()

    if assert_created_rules:
        mock_boto_elbv2_client.create_rule = Mock(
            side_effect=[
                {
                    "Rules": [
                        {
                            "RuleArn": "platform-new-web-arn",
                            "Priority": 10000,
                            "Conditions": {
                                "host-header": ["web.dev.test-app.uktrade.digital"],
                                "path-pattern": ["/*"],
                            },
                        }
                    ]
                },
                {
                    "Rules": [
                        {
                            "RuleArn": "platform-new-api-arn",
                            "Priority": 11000,
                            "Conditions": {
                                "host-header": ["api.dev.test-app.uktrade.digital"],
                                "path-pattern": ["/*"],
                            },
                        }
                    ]
                },
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

    mock_io.info.assert_has_calls([call(result) for result in expected_logs["info"]])
    mock_io.debug.assert_has_calls([call(result) for result in expected_logs["debug"]])

    if assert_created_rules:
        mock_boto_elbv2_client.create_rule.assert_has_calls(
            [
                call(
                    ListenerArn="listener-arn-doesnt-matter",
                    Priority=10000,
                    Conditions=[
                        {
                            "Field": "host-header",
                            "HostHeaderConfig": {"Values": ["web.dev.test-app.uktrade.digital"]},
                        },
                        {
                            "Field": "path-pattern",
                            "PathPatternConfig": {"Values": ["/*"]},
                        },
                    ],
                    Actions=[
                        {
                            "Type": "forward",
                            "TargetGroupArn": "tg-arn-doesnt-matter-9",
                        }
                    ],
                    Tags=[
                        {"Key": "application", "Value": "test-application"},
                        {"Key": "environment", "Value": input_args["environment"]},
                        {"Key": "service", "Value": "web"},
                        {"Key": "reason", "Value": "service"},
                        {"Key": "managed-by", "Value": "DBT Platform"},
                    ],
                )
            ]
        )

    if assert_deleted_rules:
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
    create_valid_multiple_service_config_files,
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

    mock_alb = MockALBService(
        environment="test",
    )
    mock_boto_elbv2_client = mock_alb.create_elbv2_client_mock()

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
        match="Rule update failed and rolled back",
    ):
        update_aws.update_alb_rules(
            environment="test",
        )

    mock_io.info.assert_has_calls(
        [
            call("Deployment Mode: dual-deploy-platform-traffic"),
            call("Attempting to rollback changes ..."),
            call("Rollback completed successfully"),
            call("Rolled back rules by creating: [] \n and deleting ['platform-new-web-path-arn']"),
        ]
    )

    mock_io.error.assert_has_calls(
        [
            call(
                "Error during rule update: An error occurred (ValidationError) when calling the CreateRule operation: Simulated failure"
            )
        ]
    )

    mock_boto_elbv2_client.create_rule.assert_has_calls(
        [
            call(
                ListenerArn="listener-arn-doesnt-matter",
                Priority=10000,
                Conditions=[
                    {
                        "Field": "host-header",
                        "HostHeaderConfig": {"Values": ["web.dev.test-app.uktrade.digital"]},
                    },
                    {
                        "Field": "path-pattern",
                        "PathPatternConfig": {"Values": ["/*"]},
                    },
                ],
                Actions=[
                    {
                        "Type": "forward",
                        "TargetGroupArn": "tg-arn-doesnt-matter-9",
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
            call(
                ListenerArn="listener-arn-doesnt-matter",
                Priority=10100,
                Conditions=[
                    {
                        "Field": "host-header",
                        "HostHeaderConfig": {"Values": ["api.dev.test-app.uktrade.digital"]},
                    },
                    {
                        "Field": "path-pattern",
                        "PathPatternConfig": {"Values": ["/*"]},
                    },
                ],
                Actions=[
                    {
                        "Type": "forward",
                        "TargetGroupArn": "tg-arn-doesnt-matter-10",
                    }
                ],
                Tags=[
                    {"Key": "application", "Value": "test-application"},
                    {"Key": "environment", "Value": "test"},
                    {"Key": "service", "Value": "api"},
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

    mock_alb = MockALBService(environment="production", create_platform_rules=True)
    mock_boto_elbv2_client = mock_alb.create_elbv2_client_mock()

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
        match="Rule update failed and rolled back",
    ):
        update_aws.update_alb_rules(
            environment="production",
        )

    mock_io.info.assert_has_calls(
        [
            call("Deployment Mode: copilot"),
            call("ARN: listener-rule-arn-doesnt-matter-8"),
            call("Priority: 10000"),
            call("Hosts: web.doesnt-matter"),
            call("Paths: /secondary-service/*,/secondary-service\n"),
            call("ARN: listener-rule-arn-doesnt-matter-9"),
            call("Priority: 10100"),
            call("Hosts: web.doesnt-matter"),
            call("Paths: /*\n"),
            call("ARN: listener-rule-arn-doesnt-matter-10"),
            call("Priority: 11000"),
            call("Hosts: api.doesnt-matter"),
            call("Paths: /*\n"),
            call("Attempting to rollback changes ..."),
            call("Rollback completed successfully"),
        ]
    )

    mock_io.error.assert_has_calls(
        [
            call(
                "Error during rule update: An error occurred (ValidationError) when calling the CreateRule operation: Simulated failure"
            )
        ]
    )

    mock_io.debug.assert_has_calls(
        [
            call("Listener ARN: listener-arn-doesnt-matter"),
            call("Deleted existing rule: listener-rule-arn-doesnt-matter-8"),
        ]
    )

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

    mock_alb = MockALBService(environment="test", manual_rule=True)
    mock_boto_elbv2_client = mock_alb.create_elbv2_client_mock()

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
        match="""The following rules have been created manually please review and if required set \n            the rules priority to the copilot range after priority: 48000.\n\n            Rules: \['listener-rule-arn-doesnt-matter-11'\]""",
    ):
        update_aws.update_alb_rules(
            environment="test",
        )
