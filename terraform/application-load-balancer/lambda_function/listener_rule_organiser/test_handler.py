import os
from unittest.mock import MagicMock
from unittest.mock import patch

from handler import handler
from handler import Parameters

TEST_ENVIRONMENT = {
    "APPLICATION": "myapp",
    "ENVIRONMENT": "myenv",
    "LISTENER_ARN": "arn:aws:elasticloadbalancing:us-west-2:187416307283:listener/app/alb/8e4497da625e2d8a/9ab28ade35828f96",
}


@patch.dict(os.environ, TEST_ENVIRONMENT, clear=True)
@patch("handler.DummyRuleManager")
class TestDummyHandler:
    def test_create_a_service_dummy_rule(self, dummy_rule_manager):
        service_name = "myservice"
        target_group = "target:group"
        event = {
            "service_name": service_name,
            "target_group": target_group,
            "lifecycle": {
                "action": "create",
                "prev_input": None,
            },
        }

        dummy_rule_manager_instance = MagicMock()
        dummy_rule_manager.return_value = dummy_rule_manager_instance
        handler(event, None)

        dummy_rule_manager_instance.create_rules.assert_called_with(Parameters(**event))
        dummy_rule_manager_instance.delete_rules.assert_not_called()

    def test_create_a_service_dummy_rule_without_deployment_mode(self, dummy_rule_manager):
        service_name = "myservice"
        target_group = "target:group"
        event = {
            "service_name": service_name,
            "target_group": target_group,
            "lifecycle": {
                "action": "create",
                "prev_input": None,
            },
        }

        dummy_rule_manager_instance = MagicMock()
        dummy_rule_manager.return_value = dummy_rule_manager_instance
        handler(event, None)

        dummy_rule_manager_instance.create_rules.assert_called_with(Parameters(**event))
        dummy_rule_manager_instance.delete_rules.assert_not_called()

    def test_update_a_service_dummy_rule_without_a_change(self, dummy_rule_manager):
        service_name = "myservice"
        target_group = "target:group"
        event = {
            "service_name": service_name,
            "target_group": target_group,
            "lifecycle": {
                "action": "update",
                "prev_input": {
                    "service_name": service_name,
                    "target_group": target_group,
                },
            },
        }

        dummy_rule_manager_instance = MagicMock()
        dummy_rule_manager.return_value = dummy_rule_manager_instance
        handler(event, None)

        dummy_rule_manager_instance.create_rules.assert_not_called()
        dummy_rule_manager_instance.delete_rules.assert_not_called()

    def test_update_a_service_dummy_rule_without_a_change_or_deployment_mode(self, dummy_rule_manager):
        service_name = "myservice"
        target_group = "target:group"
        event = {
            "service_name": service_name,
            "target_group": target_group,
            "lifecycle": {
                "action": "update",
                "prev_input": {
                    "service_name": service_name,
                    "target_group": target_group,
                },
            },
        }

        dummy_rule_manager_instance = MagicMock()
        dummy_rule_manager.return_value = dummy_rule_manager_instance
        handler(event, None)

        dummy_rule_manager_instance.create_rules.assert_not_called()
        dummy_rule_manager_instance.delete_rules.assert_not_called()

    def test_update_a_service_dummy_rule_with_a_change(self, dummy_rule_manager):
        service_name = "myservice"
        target_group = "target:group"
        event = {
            "service_name": service_name,
            "target_group": target_group,
            "lifecycle": {
                "action": "update",
                "prev_input": {
                    "service_name": service_name,
                    "target_group": "target:group:old",
                },
            },
        }

        dummy_rule_manager_instance = MagicMock()
        dummy_rule_manager.return_value = dummy_rule_manager_instance
        handler(event, None)

        dummy_rule_manager_instance.create_rules.assert_called_with(Parameters(**event))
        dummy_rule_manager_instance.delete_rules.assert_called_with(Parameters(**event))

    def test_delete_a_service_dummy_rule(self, dummy_rule_manager):
        service_name = "myservice"
        target_group = "target:group"
        event = {
            "service_name": service_name,
            "target_group": target_group,
            "lifecycle": {
                "action": "delete",
                "prev_input": {
                    "service_name": service_name,
                    "target_group": target_group,
                },
            },
        }

        dummy_rule_manager_instance = MagicMock()
        dummy_rule_manager.return_value = dummy_rule_manager_instance
        handler(event, None)

        dummy_rule_manager_instance.create_rules.assert_not_called()
        dummy_rule_manager_instance.delete_rules.assert_called_with(Parameters(**event))
