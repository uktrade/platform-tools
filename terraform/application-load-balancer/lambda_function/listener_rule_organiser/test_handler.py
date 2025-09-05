import os
from unittest.mock import patch, MagicMock
from handler import handler

TEST_ENVIRONMENT = {
    "APPLICATION": "myapp",
    "ENVIRONMENT": "myenv",
    "LISTENER_ARN": "arn:aws:elasticloadbalancing:us-west-2:187416307283:listener/app/alb/8e4497da625e2d8a/9ab28ade35828f96",
}


@patch.dict(os.environ, TEST_ENVIRONMENT, clear=True)
@patch('handler.DummyRuleManager')
class TestHandler:
    def test_create_new_listener_rule(self, rule_manager_mock):
        service_name = 'myservice'
        target_group = 'target:group'
        event = {
            'ServiceName': service_name,
            'TargetGroup': target_group,
            'Lifecycle': {
                'action': 'create',
                'prev_input': None,
            },
        }

        rule_manager_mock_instance = MagicMock()
        rule_manager_mock.return_value = rule_manager_mock_instance
        handler(event, None)

        rule_manager_mock_instance.create_dummy_rule.assert_called_with('target:group', 'myservice')
        rule_manager_mock_instance.delete_dummy_rule.assert_not_called()

    def test_update_a_listener_rule(self, rule_manager_mock):
        service_name = 'myservice'
        target_group = 'target:group'
        event = {
            'ServiceName': service_name,
            'TargetGroup': target_group,
            'Lifecycle': {
                'action': 'delete',
                'prev_input': {
                    'ServiceName': service_name,
                    'TargetGroup': target_group,
                },
            },
        }

        rule_manager_mock_instance = MagicMock()
        rule_manager_mock.return_value = rule_manager_mock_instance
        handler(event, None)

        rule_manager_mock_instance.create_dummy_rule.assert_not_called()
        rule_manager_mock_instance.delete_dummy_rule.assert_called_with('myservice')
