from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from moto import mock_aws

from dbt_platform_helper.providers.load_balancers import CertificateNotFoundException
from dbt_platform_helper.providers.load_balancers import ListenerNotFoundException
from dbt_platform_helper.providers.load_balancers import LoadBalancerNotFoundException
from dbt_platform_helper.providers.load_balancers import LoadBalancerProvider
from dbt_platform_helper.providers.load_balancers import (
    get_https_certificate_for_application,
)
from dbt_platform_helper.providers.load_balancers import (
    get_https_listener_for_application,
)
from dbt_platform_helper.providers.load_balancers import (
    get_load_balancer_for_application,
)
from dbt_platform_helper.providers.load_balancers import normalise_to_cidr

# TODO add exception tests for class based ALB provider


def _create_subnet(session):
    ec2 = session.client("ec2")
    vpc_id = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]

    return (
        vpc_id,
        ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24")["Subnet"]["SubnetId"],
    )


def _create_load_balancer(session):
    _, subnet_id = _create_subnet(session)
    elbv2_client = session.client("elbv2")
    return elbv2_client.create_load_balancer(
        Name="test-load-balancer",
        Subnets=[subnet_id],
        Tags=[
            {"Key": "copilot-application", "Value": "test-application"},
            {"Key": "copilot-environment", "Value": "development"},
        ],
    )["LoadBalancers"][0]["LoadBalancerArn"]


def _create_listener(session):
    elbv2_client = session.client("elbv2")
    load_balancer_arn = _create_load_balancer(session)
    return elbv2_client.create_listener(
        LoadBalancerArn=load_balancer_arn, DefaultActions=[{"Type": "forward"}], Protocol="HTTPS"
    )["Listeners"][0]["ListenerArn"]


def _create_listener_with_cert(session):
    elbv2_client = session.client("elbv2")
    listener_arn = _create_listener(session)

    acm_client = session.client("acm")
    certificate_arn = acm_client.request_certificate(
        DomainName="*.moto.com",
        CertificateAuthorityArn=f"arn:aws:acm-pca:eu-west-2:1234567890:certificate-authority/12345678-1234-1234-1234-123456789012",
    )["CertificateArn"]
    elbv2_client.add_listener_certificates(
        ListenerArn=listener_arn,
        Certificates=[{"CertificateArn": certificate_arn, "IsDefault": True}],
    )

    return certificate_arn, listener_arn


def _create_target_group(session, service_name="web"):
    ec2_client = session.client("ec2")
    vpc_response = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc_response["Vpc"]["VpcId"]

    return session.client("elbv2").create_target_group(
        Name=f"{service_name}-target-group",
        Protocol="HTTPS",
        Port=123,
        VpcId=vpc_id,
        Tags=[
            {"Key": "copilot-application", "Value": "test-application"},
            {"Key": "copilot-environment", "Value": "development"},
            {"Key": "copilot-service", "Value": service_name},
        ],
    )["TargetGroups"][0]["TargetGroupArn"]


@mock_aws
def test_get_host_header_conditions(mock_application):
    session = mock_application.environments["development"].session

    listener_arn = _create_listener(session)
    target_group_arn = _create_target_group(session)
    session.client("elbv2").create_rule(
        ListenerArn=listener_arn,
        Tags=[{"Key": "test-key", "Value": "test-value"}],
        Conditions=[{"Field": "host-header", "HostHeaderConfig": {"Values": ["/test-path"]}}],
        Priority=500,
        Actions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )

    alb_provider = LoadBalancerProvider(session)
    result = alb_provider.get_host_header_conditions(listener_arn, target_group_arn)

    assert result == [{"Field": "host-header", "HostHeaderConfig": {"Values": ["/test-path"]}}]


@mock_aws
def test_get_rules_tag_descriptions(mock_application):
    session = mock_application.environments["development"].session

    listener_arn = _create_listener(session)
    target_group_arn = _create_target_group(session)

    created_rules = session.client("elbv2").create_rule(
        ListenerArn=listener_arn,
        Tags=[{"Key": "test-key", "Value": "test-value"}],
        Conditions=[{"Field": "host-header", "HostHeaderConfig": {"Values": ["/test-path"]}}],
        Priority=500,
        Actions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )

    rules = created_rules["Rules"]
    alb_provider = LoadBalancerProvider(session)
    result = alb_provider.get_rules_tag_descriptions(rules)

    assert result[0]["Tags"] == [{"Key": "test-key", "Value": "test-value"}]


@mock_aws
def test_get_rules_tag_descriptions_by_listener_arn(mock_application):
    session = mock_application.environments["development"].session

    listener_arn = _create_listener(session)
    target_group_arn = _create_target_group(session)

    session.client("elbv2").create_rule(
        ListenerArn=listener_arn,
        Tags=[{"Key": "test-key", "Value": "test-value"}],
        Conditions=[{"Field": "host-header", "HostHeaderConfig": {"Values": ["/test-path"]}}],
        Priority=500,
        Actions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )

    alb_provider = LoadBalancerProvider(session)
    result = alb_provider.get_rules_tag_descriptions_by_listener_arn(listener_arn)

    assert result[0]["Tags"] == [{"Key": "test-key", "Value": "test-value"}]


@mock_aws
def test_create_header_rule(mock_application):
    session = mock_application.environments["development"].session

    conditions = [{"Field": "host-header", "HostHeaderConfig": {"Values": ["/test-path"]}}]

    listener_arn = _create_listener(session)
    target_group_arn = _create_target_group(session)
    session.client("elbv2").create_rule(
        ListenerArn=listener_arn,
        Tags=[{"Key": "test-key", "Value": "test-value"}],
        Conditions=conditions,
        Priority=500,
        Actions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )

    rules = session.client("elbv2").describe_rules(ListenerArn=listener_arn)["Rules"]
    assert len(rules) == 2

    mock_io = Mock()
    alb_provider = LoadBalancerProvider(session, mock_io)
    alb_provider.create_header_rule(
        listener_arn,
        target_group_arn,
        "test_header_name",
        ["1.2.3.4"],
        "test_rule_name",
        1,
        conditions,
    )

    rules = session.client("elbv2").describe_rules(ListenerArn=listener_arn)["Rules"]

    assert len(rules) == 3
    assert rules[1]["Priority"] == "1"
    assert rules[1]["Conditions"][0] == {
        "Field": "http-header",
        "HttpHeaderConfig": {"HttpHeaderName": "test_header_name", "Values": ["1.2.3.4"]},
    }

    mock_io.info.assert_called_once_with(
        f"Creating listener rule test_rule_name for HTTPS Listener with arn {listener_arn}.\n\nIf request header test_header_name contains one of the values ['1.2.3.4'], the request will be forwarded to target group with arn {target_group_arn}."
    )


@pytest.mark.parametrize(
    "allowed_ips, expected_rule_cidr",
    [
        (
            ["1.2.3.4", "5.6.7.8"],
            ["1.2.3.4/32", "5.6.7.8/32"],
        ),
        (
            ["1.2.3.4/32", "5.6.7.8/24"],
            ["1.2.3.4/32", "5.6.7.8/24"],
        ),
    ],
)
@mock_aws
def test_create_source_ip_rule(allowed_ips, expected_rule_cidr, mock_application):
    session = mock_application.environments["development"].session

    conditions = [{"Field": "host-header", "HostHeaderConfig": {"Values": ["/test-path"]}}]

    listener_arn = _create_listener(session)
    target_group_arn = _create_target_group(session)
    session.client("elbv2").create_rule(
        ListenerArn=listener_arn,
        Tags=[{"Key": "test-key", "Value": "test-value"}],
        Conditions=conditions,
        Priority=500,
        Actions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )

    mock_io = Mock()
    alb_provider = LoadBalancerProvider(session, mock_io)
    alb_provider.create_source_ip_rule(
        listener_arn, target_group_arn, allowed_ips, "test_rule_name", 1, conditions
    )

    rules = session.client("elbv2").describe_rules(ListenerArn=listener_arn)["Rules"]

    assert len(rules) == 3
    assert rules[1]["Priority"] == "1"
    assert rules[1]["Conditions"][0] == {
        "Field": "source-ip",
        "SourceIpConfig": {"Values": sorted(expected_rule_cidr)},
    }

    mock_io.info.assert_called_once_with(
        f"Creating listener rule test_rule_name for HTTPS Listener with arn {listener_arn}.\n\nIf request source ip matches one of the values {allowed_ips}, the request will be forwarded to target group with arn {target_group_arn}."
    )


@mock_aws
def test_find_target_group(mock_application):
    session = mock_application.environments["development"].session

    _create_listener(session)
    target_group_arn = _create_target_group(session)

    mock_io = Mock()
    alb_provider = LoadBalancerProvider(session, mock_io)
    result = alb_provider.find_target_group("test-application", "development", "web")

    assert result == target_group_arn


@mock_aws
def test_find_target_group_not_found(mock_application):
    session = mock_application.environments["development"].session

    _create_listener(session)
    _create_target_group(session)

    mock_io = Mock()
    alb_provider = LoadBalancerProvider(session, mock_io)
    result = alb_provider.find_target_group("unfindable-application", "development", "web")

    assert result == None
    mock_io.error.assert_called_once_with(
        "No target group found for application: unfindable-application, environment: development, service: web"
    )


@mock_aws
def test_delete_listener_rule(mock_application):
    session = mock_application.environments["development"].session

    listener_arn = _create_listener(session)
    target_group_arn = _create_target_group(session)

    rules = session.client("elbv2").create_rule(
        ListenerArn=listener_arn,
        Tags=[{"Key": "name", "Value": "test_rule_name"}],
        Conditions=[{"Field": "host-header", "HostHeaderConfig": {"Values": ["/test-path"]}}],
        Priority=500,
        Actions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )
    expected_arn = rules["Rules"][0]["RuleArn"]

    rules = session.client("elbv2").describe_rules(ListenerArn=listener_arn)["Rules"]
    assert len(rules) == 2

    alb_provider = LoadBalancerProvider(session)
    result = alb_provider.delete_listener_rule_by_tags(
        [{"Tags": [{"Key": "name", "Value": "test_rule_name"}], "ResourceArn": expected_arn}],
        "test_rule_name",
    )

    rules = session.client("elbv2").describe_rules(ListenerArn=listener_arn)["Rules"]

    assert len(rules) == 1  # only default rule
    assert result == expected_arn


@mock_aws
def test_create_rule(mock_application):
    session = mock_application.environments["development"].session

    listener_arn = _create_listener(session)

    rules = session.client("elbv2").describe_rules(ListenerArn=listener_arn)["Rules"]
    assert len(rules) == 1

    alb_provider = LoadBalancerProvider(session)
    alb_provider.create_rule(
        listener_arn,
        actions=[],
        conditions=[],
        priority=111,
        tags=[{"Key": "doesnt", "Value": "matter"}],
    )

    rules = session.client("elbv2").describe_rules(ListenerArn=listener_arn)["Rules"]
    assert len(rules) == 2
    tags_descriptions = session.client("elbv2").describe_tags(
        ResourceArns=[rule["RuleArn"] for rule in rules]
    )

    assert rules[0]["Priority"] == "111"
    assert rules[0]["Conditions"] == []
    assert rules[0]["Actions"] == []
    assert tags_descriptions["TagDescriptions"][0]["Tags"] == [{"Key": "doesnt", "Value": "matter"}]


@mock_aws
def test_get_load_balancer_for_application(mock_application):
    session = mock_application.environments["development"].session
    lb_arn = _create_load_balancer(session)

    alb_provider = LoadBalancerProvider(session)
    result = alb_provider.get_load_balancer_for_application("test-application", "development")

    assert result == lb_arn


@mock_aws
def test_get_https_listener_for_application(mock_application):
    session = mock_application.environments["development"].session
    listerner_arn = _create_listener(session)

    alb_provider = LoadBalancerProvider(session)
    result = alb_provider.get_https_listener_for_application("test-application", "development")

    assert result == listerner_arn


@mock_aws
def test_https_certificate_for_application(mock_application):
    session = mock_application.environments["development"].session
    certificate_arn, _ = _create_listener_with_cert(session)

    # TODO mocking because isDeafult is lost when adding cert to listener https://github.com/getmoto/moto/blob/9e8bc74f3610ed390e7fad4bb90af574b68dd1f1/moto/elbv2/models.py#L2017
    mock_response = {"Certificates": [{"CertificateArn": certificate_arn, "IsDefault": True}]}
    alb_provider = LoadBalancerProvider(session)
    with patch.object(
        alb_provider.evlb_client, "describe_listener_certificates", return_value=mock_response
    ):
        result = alb_provider.get_https_certificate_for_application(
            "test-application", "development"
        )
        assert result == certificate_arn


@pytest.mark.parametrize(
    "ip, expected_cidr",
    [
        (
            "1.2.3.4",
            "1.2.3.4/32",
        ),
        (
            "1.2.3.4/32",
            "1.2.3.4/32",
        ),
        (
            "1.2.3.4/128",
            "1.2.3.4/128",
        ),
    ],
)
def test_normalise_to_cidr(ip, expected_cidr):
    assert normalise_to_cidr(ip) == expected_cidr


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
    @patch(
        "dbt_platform_helper.providers.load_balancers.get_https_listener_for_application",
        return_value="https_listener_arn",
    )
    def test_when_no_certificate_present(self, mock_get_https_listener_for_application):
        boto_mock = MagicMock()
        boto_mock.client().describe_listener_certificates.return_value = {"Certificates": []}

        with pytest.raises(CertificateNotFoundException):
            get_https_certificate_for_application(boto_mock, "test-application", "development")

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
