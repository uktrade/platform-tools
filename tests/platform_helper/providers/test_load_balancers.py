from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from dbt_platform_helper.providers.load_balancers import ListenerNotFoundException
from dbt_platform_helper.providers.load_balancers import LoadBalancerNotFoundException
from dbt_platform_helper.providers.load_balancers import (
    get_https_certificate_for_application,
)
from dbt_platform_helper.providers.load_balancers import (
    get_https_listener_for_application,
)
from dbt_platform_helper.providers.load_balancers import (
    get_load_balancer_for_application,
)


class TestFindHTTPSListener:
    @patch(
        "dbt_platform_helper.providers.load_balancers.get_load_balancer_for_application",
        return_value="lb_arn",
    )
    def test_when_no_https_listener_present(self, get_load_balancer_for_application):
        boto_mock = MagicMock()
        boto_mock.client().describe_listeners.return_value = {"Listeners": []}
        with pytest.raises(ListenerNotFoundException):
            get_https_listener_for_application(boto_mock, "test-application", "development")

    @patch(
        "dbt_platform_helper.providers.load_balancers.get_load_balancer_for_application",
        return_value="lb_arn",
    )
    def test_when_https_listener_present(self, get_load_balancer_for_application):

        boto_mock = MagicMock()
        boto_mock.client().describe_listeners.return_value = {
            "Listeners": [{"ListenerArn": "listener_arn", "Protocol": "HTTPS"}]
        }

        listener_arn = get_https_listener_for_application(
            boto_mock, "test-application", "development"
        )
        assert "listener_arn" == listener_arn


class TestFindLoadBalancer:
    def test_when_no_load_balancer_exists(self):

        boto_mock = MagicMock()
        boto_mock.client().describe_load_balancers.return_value = {"LoadBalancers": []}
        with pytest.raises(LoadBalancerNotFoundException):
            get_load_balancer_for_application(boto_mock, "test-application", "development")

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

        lb_arn = get_load_balancer_for_application(boto_mock, "test-application", "development")
        assert "lb_arn" == lb_arn


class TestGetHttpsCertificateForApplicationLoadbalancer:
    # @patch(
    #     "dbt_platform_helper.domain.copilot_environment.get_https_listener_for_application",
    #     return_value="https_listener_arn",
    # )
    # def test_when_no_certificate_present(self, mock_get_https_listener_for_application):
    #     boto_mock = MagicMock()
    #     boto_mock.client().describe_listener_certificates.return_value = {"Certificates": []}

    #     with pytest.raises(CertificateNotFoundException):
    #         find_https_certificate(boto_mock, "test-application", "development")

    @patch(
        "dbt_platform_helper.providers.load_balancers.get_https_listener_for_application",
        return_value="https_listener_arn",
    )
    def test_when_single_https_certificate_present(self, mock_get_https_listener_for_application):
        boto_mock = MagicMock()
        boto_mock.client().describe_listener_certificates.return_value = {
            "Certificates": [{"CertificateArn": "certificate_arn", "IsDefault": "True"}]
        }

        certificate_arn = get_https_certificate_for_application(
            boto_mock, "test-application", "development"
        )
        assert "certificate_arn" == certificate_arn

    @patch(
        "dbt_platform_helper.providers.load_balancers.get_https_listener_for_application",
        return_value="https_listener_arn",
    )
    def test_when_multiple_https_certificate_present(self, mock_get_https_listener_for_application):
        boto_mock = MagicMock()
        boto_mock.client().describe_listener_certificates.return_value = {
            "Certificates": [
                {"CertificateArn": "certificate_arn_default", "IsDefault": "True"},
                {"CertificateArn": "certificate_arn_not_default", "IsDefault": "False"},
            ]
        }

        certificate_arn = get_https_certificate_for_application(
            boto_mock, "test-application", "development"
        )
        assert "certificate_arn_default" == certificate_arn
