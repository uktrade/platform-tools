from unittest.mock import MagicMock

from dummy_rule_manager import DummyRuleManager
from dummy_rule_manager import create_chunk_iterator


class TestDummyRuleManagerCreate:
    def test_create_when_this_is_the_first_dummy_rule(self):
        mock_rules = {
            "Rules": [
                {
                    "RuleArn": "copilot:rule",
                    "Priority": 48000,
                },
            ]
        }
        mock_rule_tags = {
            "TagDescriptions": [
                {
                    "ResourceArn": "copilot:rule",
                    "Tags": [
                        {"Key": "Name", "Value": "test"},
                    ],
                }
            ]
        }
        mock_client = MagicMock()
        mock_rules_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_rules_paginator
        mock_rules_paginator.paginate.return_value = [mock_rules]
        mock_client.describe_tags.return_value = mock_rule_tags
        mock_client.create_rule.return_value = None

        organiser = DummyRuleManager("myapp", "myenv", "listener_arn")
        organiser.get_client = MagicMock(return_value=mock_client)

        organiser.create_dummy_rule("target:group", "myservice")

        mock_client.get_paginator.assert_called_once_with("describe_rules")
        mock_rules_paginator.paginate.assert_called_once_with(ListenerArn="listener_arn")
        mock_client.describe_tags.assert_called_once_with(ResourceArns=["copilot:rule"])
        mock_client.create_rule.assert_called_once_with(
            ListenerArn="listener_arn",
            Conditions=[
                {
                    "Field": "host-header",
                    "HostHeaderConfig": {"Values": ["myservice.dummy"]},
                }
            ],
            Priority=1000,
            Actions=[
                {
                    "Type": "forward",
                    "TargetGroupArn": "target:group",
                }
            ],
            Tags=[
                {
                    "Key": "application",
                    "Value": "myapp",
                },
                {
                    "Key": "environment",
                    "Value": "myenv",
                },
                {
                    "Key": "service",
                    "Value": "myservice",
                },
                {
                    "Key": "managed-by",
                    "Value": "DBT Platform - Service Terraform",
                },
                {
                    "Key": "reason",
                    "Value": "DummyRule",
                },
            ],
        )

    def test_create_when_this_is_not_the_first_dummy_rule(self):
        mock_rules = {
            "Rules": [
                {
                    "RuleArn": "dummy:rule",
                    "Priority": 1000,
                },
                {
                    "RuleArn": "copilot:rule",
                    "Priority": 48000,
                },
            ]
        }
        mock_rule_tags = {
            "TagDescriptions": [
                {
                    "ResourceArn": "dummy:rule",
                    "Tags": [
                        {"Key": "application", "Value": "myapp"},
                        {"Key": "environment", "Value": "myenv"},
                        {"Key": "service", "Value": "anotherservice"},
                        {"Key": "managed-by", "Value": "DBT Platform - Service Terraform"},
                        {"Key": "reason", "Value": "DummyRule"},
                    ],
                },
                {
                    "ResourceArn": "copilot:rule",
                    "Tags": [
                        {"Key": "Name", "Value": "test"},
                    ],
                },
            ]
        }
        mock_client = MagicMock()
        mock_rules_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_rules_paginator
        mock_rules_paginator.paginate.return_value = [mock_rules]
        mock_client.describe_tags.return_value = mock_rule_tags
        mock_client.create_rule.return_value = None

        organiser = DummyRuleManager("myapp", "myenv", "listener_arn")
        organiser.get_client = MagicMock(return_value=mock_client)

        organiser.create_dummy_rule("target:group", "myservice")

        mock_client.get_paginator.assert_called_once_with("describe_rules")
        mock_rules_paginator.paginate.assert_called_once_with(ListenerArn="listener_arn")
        mock_client.describe_tags.assert_called_once_with(
            ResourceArns=["dummy:rule", "copilot:rule"]
        )
        mock_client.create_rule.assert_called_once_with(
            ListenerArn="listener_arn",
            Conditions=[
                {
                    "Field": "host-header",
                    "HostHeaderConfig": {"Values": ["myservice.dummy"]},
                }
            ],
            Priority=1001,
            Actions=[
                {
                    "Type": "forward",
                    "TargetGroupArn": "target:group",
                }
            ],
            Tags=[
                {
                    "Key": "application",
                    "Value": "myapp",
                },
                {
                    "Key": "environment",
                    "Value": "myenv",
                },
                {
                    "Key": "service",
                    "Value": "myservice",
                },
                {
                    "Key": "managed-by",
                    "Value": "DBT Platform - Service Terraform",
                },
                {
                    "Key": "reason",
                    "Value": "DummyRule",
                },
            ],
        )

    def test_create_when_dummy_rule_exists_for_the_service(self):
        mock_rules = {
            "Rules": [
                {
                    "RuleArn": "dummy:rule",
                    "Priority": 1000,
                },
                {
                    "RuleArn": "copilot:rule",
                    "Priority": 48000,
                },
            ]
        }
        mock_rule_tags = {
            "TagDescriptions": [
                {
                    "ResourceArn": "dummy:rule",
                    "Tags": [
                        {"Key": "application", "Value": "myapp"},
                        {"Key": "environment", "Value": "myenv"},
                        {"Key": "service", "Value": "myservice"},
                        {"Key": "managed-by", "Value": "DBT Platform - Service Terraform"},
                        {"Key": "reason", "Value": "DummyRule"},
                    ],
                },
                {
                    "ResourceArn": "copilot:rule",
                    "Tags": [
                        {"Key": "Name", "Value": "test"},
                    ],
                },
            ]
        }
        mock_client = MagicMock()
        mock_rules_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_rules_paginator
        mock_rules_paginator.paginate.return_value = [mock_rules]
        mock_client.describe_tags.return_value = mock_rule_tags
        mock_client.create_rule.return_value = None

        organiser = DummyRuleManager("myapp", "myenv", "listener_arn")
        organiser.get_client = MagicMock(return_value=mock_client)

        organiser.create_dummy_rule("target:group", "myservice")

        mock_client.get_paginator.assert_called_once_with("describe_rules")
        mock_rules_paginator.paginate.assert_called_once_with(ListenerArn="listener_arn")
        mock_client.describe_tags.assert_called_once_with(
            ResourceArns=["dummy:rule", "copilot:rule"]
        )
        mock_client.create_rule.assert_not_called()

    def test_delete_when_this_is_the_only_dummy_rule(self):
        mock_rules = {
            "Rules": [
                {
                    "RuleArn": "dummy:rule",
                    "Priority": 1000,
                },
                {
                    "RuleArn": "copilot:rule",
                    "Priority": 48000,
                },
            ]
        }
        mock_rule_tags = {
            "TagDescriptions": [
                {
                    "ResourceArn": "dummy:rule",
                    "Tags": [
                        {"Key": "application", "Value": "myapp"},
                        {"Key": "environment", "Value": "myenv"},
                        {"Key": "service", "Value": "myservice"},
                        {"Key": "managed-by", "Value": "DBT Platform - Service Terraform"},
                        {"Key": "reason", "Value": "DummyRule"},
                    ],
                },
                {
                    "ResourceArn": "copilot:rule",
                    "Tags": [
                        {"Key": "Name", "Value": "test"},
                    ],
                },
            ]
        }
        mock_client = MagicMock()
        mock_rules_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_rules_paginator
        mock_rules_paginator.paginate.return_value = [mock_rules]
        mock_client.describe_tags.return_value = mock_rule_tags
        mock_client.create_rule.return_value = None
        mock_client.delete_rule.return_value = None

        organiser = DummyRuleManager("myapp", "myenv", "listener_arn")
        organiser.get_client = MagicMock(return_value=mock_client)

        organiser.delete_dummy_rule("myservice")

        mock_client.get_paginator.assert_called_once_with("describe_rules")
        mock_rules_paginator.paginate.assert_called_once_with(ListenerArn="listener_arn")
        mock_client.describe_tags.assert_called_once_with(
            ResourceArns=["dummy:rule", "copilot:rule"]
        )
        mock_client.create_rule.assert_not_called()
        mock_client.delete_rule.assert_called_once_with(RuleArn="dummy:rule")

    def test_delete_when_this_is_one_of_many_dummy_rules(self):
        mock_rules = {
            "Rules": [
                {
                    "RuleArn": "dummy:rule1",
                    "Priority": 1000,
                },
                {
                    "RuleArn": "dummy:rule2",
                    "Priority": 1001,
                },
                {
                    "RuleArn": "copilot:rule",
                    "Priority": 48000,
                },
            ]
        }
        mock_rule_tags = {
            "TagDescriptions": [
                {
                    "ResourceArn": "dummy:rule1",
                    "Tags": [
                        {"Key": "application", "Value": "myapp"},
                        {"Key": "environment", "Value": "myenv"},
                        {"Key": "service", "Value": "myservice"},
                        {"Key": "managed-by", "Value": "DBT Platform - Service Terraform"},
                        {"Key": "reason", "Value": "DummyRule"},
                    ],
                },
                {
                    "ResourceArn": "dummy:rule2",
                    "Tags": [
                        {"Key": "application", "Value": "myapp"},
                        {"Key": "environment", "Value": "myenv"},
                        {"Key": "service", "Value": "anotherservice"},
                        {"Key": "managed-by", "Value": "DBT Platform - Service Terraform"},
                        {"Key": "reason", "Value": "DummyRule"},
                    ],
                },
                {
                    "ResourceArn": "copilot:rule",
                    "Tags": [
                        {"Key": "Name", "Value": "test"},
                    ],
                },
            ]
        }
        mock_client = MagicMock()
        mock_rules_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_rules_paginator
        mock_rules_paginator.paginate.return_value = [mock_rules]
        mock_client.describe_tags.return_value = mock_rule_tags
        mock_client.create_rule.return_value = None
        mock_client.delete_rule.return_value = None

        organiser = DummyRuleManager("myapp", "myenv", "listener_arn")
        organiser.get_client = MagicMock(return_value=mock_client)

        organiser.delete_dummy_rule("myservice")

        mock_client.get_paginator.assert_called_once_with("describe_rules")
        mock_rules_paginator.paginate.assert_called_once_with(ListenerArn="listener_arn")
        mock_client.describe_tags.assert_called_once_with(
            ResourceArns=["dummy:rule1", "dummy:rule2", "copilot:rule"]
        )
        mock_client.create_rule.assert_not_called()
        mock_client.delete_rule.assert_called_once_with(RuleArn="dummy:rule1")

    def test_delete_when_the_dummy_rule_does_not_exist(self):
        mock_rules = {
            "Rules": [
                {
                    "RuleArn": "copilot:rule",
                    "Priority": 48000,
                },
            ]
        }
        mock_rule_tags = {
            "TagDescriptions": [
                {
                    "ResourceArn": "copilot:rule",
                    "Tags": [
                        {"Key": "Name", "Value": "test"},
                    ],
                }
            ]
        }
        mock_client = MagicMock()
        mock_rules_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_rules_paginator
        mock_rules_paginator.paginate.return_value = [mock_rules]
        mock_client.describe_tags.return_value = mock_rule_tags
        mock_client.create_rule.return_value = None
        mock_client.delete_rule.return_value = None

        organiser = DummyRuleManager("myapp", "myenv", "listener_arn")
        organiser.get_client = MagicMock(return_value=mock_client)

        organiser.delete_dummy_rule("myservice")

        mock_client.get_paginator.assert_called_once_with("describe_rules")
        mock_rules_paginator.paginate.assert_called_once_with(ListenerArn="listener_arn")
        mock_client.describe_tags.assert_called_once_with(ResourceArns=["copilot:rule"])
        mock_client.create_rule.assert_not_called()


class TestListChunkIterator:
    def test_creating_equally_sized_chunks_from_a_list(self):
        unchunked_list = [1, 2, 3, 4]
        chunked_list = list(create_chunk_iterator(unchunked_list, 2))

        assert [[1, 2], [3, 4]] == chunked_list

    def test_creating_unequally_sized_chunks_from_a_list(self):
        unchunked_list = [1, 2, 3]
        chunked_list = list(create_chunk_iterator(unchunked_list, 2))

        assert [[1, 2], [3]] == chunked_list
