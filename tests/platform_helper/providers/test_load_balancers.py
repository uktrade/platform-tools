from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from dbt_platform_helper.providers.load_balancers import ListenerNotFoundError
from dbt_platform_helper.providers.load_balancers import LoadBalancerNotFoundError
from dbt_platform_helper.providers.load_balancers import find_https_listener
from dbt_platform_helper.providers.load_balancers import find_load_balancer


class TestFindHTTPSListener:
    @patch("dbt_platform_helper.providers.load_balancers.find_load_balancer", return_value="lb_arn")
    def test_when_no_https_listener_present(self, find_load_balancer):
        boto_mock = MagicMock()
        boto_mock.client().describe_listeners.return_value = {"Listeners": []}
        with pytest.raises(ListenerNotFoundError):
            find_https_listener(boto_mock, "test-application", "development")

    @patch("dbt_platform_helper.providers.load_balancers.find_load_balancer", return_value="lb_arn")
    def test_when_https_listener_present(self, find_load_balancer):

        boto_mock = MagicMock()
        boto_mock.client().describe_listeners.return_value = {
            "Listeners": [{"ListenerArn": "listener_arn", "Protocol": "HTTPS"}]
        }

        listener_arn = find_https_listener(boto_mock, "test-application", "development")
        assert "listener_arn" == listener_arn


class TestFindLoadBalancer:
    def test_when_no_load_balancer_exists(self):

        boto_mock = MagicMock()
        boto_mock.client().describe_load_balancers.return_value = {"LoadBalancers": []}
        with pytest.raises(LoadBalancerNotFoundError):
            find_load_balancer(boto_mock, "test-application", "development")

    def test_when_a_load_balancer_exists(self):

        boto_mock = MagicMock()
        boto_mock.client().describe_load_balancers.return_value = {
            "LoadBalancers": [{"LoadBalancerArn": "lb_arn"}]
        }
        boto_mock.client().describe_tags.return_value = {
            "TagDescriptions": [
                {
                    "ResourceArn": "lb_arn",
                    "Tags": [
                        {"Key": "copilot-application", "Value": "test-application"},
                        {"Key": "copilot-environment", "Value": "development"},
                    ],
                }
            ]
        }

        lb_arn = find_load_balancer(boto_mock, "test-application", "development")
        assert "lb_arn" == lb_arn
