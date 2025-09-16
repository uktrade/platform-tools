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
        # (
        #     {
        #         "environment": "production",
        #     },
        #     ["Deployment Mode: copilot", "ARN: listener-arn-doesnt-matter"],
        #     False,
        # ),
        # (
        #     {
        #         "environment": "development",
        #     },
        #     ["Deployment Mode: dual-deploy-copilot-traffic", "ARN: listener-arn-doesnt-matter"],
        #     False,
        # ),
        # (
        #     {
        #         "environment": "test",
        #     },
        #     ["Deployment Mode: dual-deploy-platform-traffic", "ARN: listener-arn-doesnt-matter"],
        #     False,
        # ),
        (
            {
                "environment": "staging",
            },
            [
                "Deployment Mode: platform",
                "ARN: listener-arn-doesnt-matter",
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-1",
                "Updated forward action for service web-path to use: tg-arn-doesnt-matter-2",
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-2",
                "Updated forward action for service api to use: tg-arn-doesnt-matter-3",
                "Building platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-3",
                "Updated forward action for service web to use: tg-arn-doesnt-matter-1",
                "Creating platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-1",
                "Creating platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-3",
                "Creating platform rule for corresponding copilot rule: listener-rule-arn-doesnt-matter-2",
                "Created rules: ['platform-new-web-path-arn', 'platform-new-web-arn', 'platform-new-api-arn']",
            ],
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
                    "RuleArn": "listener-rule-arn-doesnt-matter-5",
                    "Priority": "1",
                    "Conditions": [
                        {
                            "Field": "http-header",
                            "HttpHeaderConfig": {
                                "HttpHeaderName": "X-Forwarded-For",
                                "Values": ["10.10.10.100"],
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
                    "ResourceArn": "listener-rule-arn-doesnt-matter-5",
                },
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-6",
                    "Priority": "2",
                    "Conditions": [
                        {
                            "Field": "host-header",
                            "Values": ["web.doesnt-matter"],
                            "HostHeaderConfig": {"Values": ["web.doesnt-matter"]},
                        },
                        {"Field": "source-ip", "SourceIpConfig": {"Values": ["10.10.10.100/32"]}},
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
                    "ResourceArn": "listener-rule-arn-doesnt-matter-6",
                },
                {
                    "RuleArn": "listener-rule-arn-doesnt-matter-7",
                    "Priority": "3",
                    "Conditions": [
                        {
                            "Field": "host-header",
                            "Values": ["api.doesnt-matter"],
                            "HostHeaderConfig": {"Values": ["web.doesnt-matter"]},
                        },
                        {
                            "Field": "http-header",
                            "HttpHeaderConfig": {
                                "HttpHeaderName": "Bypass-Key",
                                "Values": ["xxxxxxxx"],
                            },
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
                    "ResourceArn": "listener-rule-arn-doesnt-matter-7",
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
                            "TargetGroupArn": "tg-arn-doesnt-matter-4",
                            "TargetGroupName": "web-tg-zzzzz",
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
                            "TargetGroupArn": "tg-arn-doesnt-matter-5",
                            "TargetGroupName": "web-tg-wwwwww",
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
                            "TargetGroupArn": "tg-arn-doesnt-matter-6",
                            "TargetGroupName": "web-tg-ppppp",
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
                            {"Key": "copilot-environment", "Value": input_args["environment"]},
                        ],
                    },
                ]
            },
            {
                "TagDescriptions": [
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-5",
                        "Tags": [
                            {"Key": "name", "Value": "AllowedIps"},
                            {"Key": "service", "Value": "web"},
                        ],
                    },
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-6",
                        "Tags": [
                            {"Key": "name", "Value": "AllowedSourceIps"},
                            {"Key": "service", "Value": "web"},
                        ],
                    },
                    {
                        "ResourceArn": "listener-rule-arn-doesnt-matter-7",
                        "Tags": [
                            {"Key": "name", "Value": "BypassIpFilter"},
                            {"Key": "service", "Value": "web"},
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
            {
                "TagDescriptions": [
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-1",
                        "Tags": [
                            {"Key": "environment", "Value": input_args["environment"]},
                            {"Key": "application", "Value": "test-application"},
                            {"Key": "managed-by", "Value": "DBT Platform - Service Terraform"},
                            {"Key": "service", "Value": "web"},
                        ],
                    },
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-2",
                        "Tags": [
                            {"Key": "environment", "Value": input_args["environment"]},
                            {"Key": "application", "Value": "test-application"},
                            {"Key": "managed-by", "Value": "DBT Platform - Service Terraform"},
                            {"Key": "service", "Value": "web-path"},
                        ],
                    },
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-3",
                        "Tags": [
                            {"Key": "environment", "Value": input_args["environment"]},
                            {"Key": "application", "Value": "test-application"},
                            {"Key": "managed-by", "Value": "DBT Platform - Service Terraform"},
                            {"Key": "service", "Value": "api"},
                        ],
                    },
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-4",
                        "Tags": [
                            {"Key": "environment", "Value": "different-env"},
                            {"Key": "application", "Value": "test-application"},
                            {"Key": "managed-by", "Value": "DBT Platform - Service Terraform"},
                            {"Key": "service", "Value": "web"},
                        ],
                    },
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-5",
                        "Tags": [
                            {"Key": "environment", "Value": input_args["environment"]},
                            {"Key": "application", "Value": "different-application"},
                            {"Key": "managed-by", "Value": "DBT Platform - Service Terraform"},
                            {"Key": "service", "Value": "web"},
                        ],
                    },
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-6",
                        "Tags": [
                            {"Key": "copilot-application", "Value": "test-application"},
                            {"Key": "copilot-environment", "Value": input_args["environment"]},
                            {"Key": "environment", "Value": input_args["environment"]},
                            {"Key": "application", "Value": "test-application"},
                            {"Key": "managed-by", "Value": "DBT Platform - Terraform"},
                        ],
                    },
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-7",
                        "Tags": [
                            {"Key": "copilot-application", "Value": "test-application"},
                            {"Key": "copilot-environment", "Value": input_args["environment"]},
                            {"Key": "copilot-service", "Value": "web-path"},
                        ],
                    },
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-8",
                        "Tags": [
                            {"Key": "copilot-application", "Value": "test-application"},
                            {"Key": "copilot-environment", "Value": input_args["environment"]},
                            {"Key": "copilot-service", "Value": "api"},
                        ],
                    },
                    {
                        "ResourceArn": "tg-arn-doesnt-matter-9",
                        "Tags": [
                            {"Key": "copilot-application", "Value": "test-application"},
                            {"Key": "copilot-environment", "Value": input_args["environment"]},
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
                            {"Key": "copilot-environment", "Value": input_args["environment"]},
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
                            {"Key": "copilot-environment", "Value": input_args["environment"]},
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
                            {"Key": "copilot-environment", "Value": input_args["environment"]},
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
            {"Rules": [{"RuleArn": "platform-new-web-arn"}]},
            {"Rules": [{"RuleArn": "platform-new-api-arn"}]},
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
                Actions=[{"Type": "forward", "TargetGroupArn": "tg-arn-doesnt-matter-2"}],
                Tags=[
                    {"Key": "application", "Value": "test-application"},
                    {"Key": "environment", "Value": "staging"},
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
                Actions=[{"Type": "forward", "TargetGroupArn": "tg-arn-doesnt-matter-1"}],
                Tags=[
                    {"Key": "application", "Value": "test-application"},
                    {"Key": "environment", "Value": "staging"},
                    {"Key": "service", "Value": "web"},
                    {"Key": "reason", "Value": "service"},
                    {"Key": "managed-by", "Value": "DBT Platform"},
                ],
            ),
            call(
                ListenerArn="listener-arn-doesnt-matter",
                Priority=11000,
                Conditions=[
                    {"Field": "path-pattern", "Values": ["/*"]},
                    {"Field": "host-header", "Values": ["api.doesnt-matter"]},
                ],
                Actions=[{"Type": "forward", "TargetGroupArn": "tg-arn-doesnt-matter-3"}],
                Tags=[
                    {"Key": "application", "Value": "test-application"},
                    {"Key": "environment", "Value": "staging"},
                    {"Key": "service", "Value": "api"},
                    {"Key": "reason", "Value": "service"},
                    {"Key": "managed-by", "Value": "DBT Platform"},
                ],
            ),
        ]
    )


# TODO test manual rule
# TODO test delete platform rules
# TODO test delete platform rules copilot mode
# TODO test rollback and errors
