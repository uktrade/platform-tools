from pathlib import Path
from unittest.mock import mock_open
from unittest.mock import patch

import boto3
from click.testing import CliRunner
from moto import mock_cloudformation
from moto import mock_ec2
from moto import mock_ecs
from moto import mock_elbv2
from moto import mock_sts
from moto import mock_wafv2

from commands.waf_cli import attach_waf
from commands.waf_cli import check_waf
from commands.waf_cli import custom_waf


@mock_wafv2
def test_check_waf():
    session = boto3.Session()
    arn = session.client("wafv2").create_web_acl(
        Name="default",
        Scope="REGIONAL",
        DefaultAction={},
        VisibilityConfig={"SampledRequestsEnabled": True, "CloudWatchMetricsEnabled": True, "MetricName": "blah"},
    )["Summary"]["ARN"]

    assert check_waf(session) == arn


@mock_wafv2
def test_check_waf_no_arn():
    session = boto3.Session()
    session.client("wafv2").create_web_acl(
        Name="non-default",
        Scope="REGIONAL",
        DefaultAction={},
        VisibilityConfig={"SampledRequestsEnabled": True, "CloudWatchMetricsEnabled": True, "MetricName": "blah"},
    )["Summary"]["ARN"]

    assert check_waf(session) == ""


@mock_sts
@mock_wafv2
def test_attach_waf_no_default(alias_session):
    boto3.Session().client("wafv2").create_web_acl(
        Name="non-default",
        Scope="REGIONAL",
        DefaultAction={},
        VisibilityConfig={"SampledRequestsEnabled": True, "CloudWatchMetricsEnabled": True, "MetricName": "blah"},
    )["Summary"]["ARN"]
    runner = CliRunner()
    result = runner.invoke(attach_waf, ["--app", "app", "--project-profile", "foo", "--svc", "svc", "--env", "env"])

    assert "Default WAF rule does not exists in this AWS account," in result.output


@mock_ec2
@mock_ecs
@mock_elbv2
@mock_sts
@mock_wafv2
def test_attach_waf(alias_session):
    session = boto3.Session()
    vpc_id = session.client("ec2").create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnet_id = session.client("ec2").create_subnet(VpcId=vpc_id, CidrBlock="10.0.0.0/16")["Subnet"]["SubnetId"]
    elbv2_client = session.client("elbv2")
    lb_response = elbv2_client.create_load_balancer(Name="foo", Subnets=[subnet_id])
    dns_name = lb_response["LoadBalancers"][0]["DNSName"]
    lb_arn = lb_response["LoadBalancers"][0]["LoadBalancerArn"]
    target_group_arn = elbv2_client.create_target_group(Name="foo")["TargetGroups"][0]["TargetGroupArn"]
    elbv2_client.create_listener(
        LoadBalancerArn=lb_arn, DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}]
    )
    ecs_client = session.client("ecs")
    ecs_client.create_cluster(clusterName="app-env-svc")
    ecs_client.create_service(
        cluster="app-env-svc",
        serviceName="app-env-svc",
        loadBalancers=[{"loadBalancerName": "foo", "targetGroupArn": target_group_arn}],
    )
    open_mock = mock_open(read_data='{"environments": {"env": {"http": {"alias": "blah"}}}}')
    acl_arn = session.client("wafv2").create_web_acl(
        Name="default",
        Scope="REGIONAL",
        DefaultAction={},
        VisibilityConfig={"SampledRequestsEnabled": True, "CloudWatchMetricsEnabled": True, "MetricName": "blah"},
    )["Summary"]["ARN"]
    runner = CliRunner()
    response = session.client("wafv2").get_web_acl_for_resource(ResourceArn=lb_arn)

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    with patch("commands.dns_cli.open", open_mock):
        result = runner.invoke(
            attach_waf, ["--app", "app", "--project-profile", "foo", "--svc", "svc", "--env", "env"]
        )

    assert f"Default WAF is now associated with {dns_name} for domain blah" in result.output

    response = session.client("wafv2").get_web_acl_for_resource(ResourceArn=lb_arn)

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    # We should have more assertions here, but currently moto only supports associating apigateway stages, so it's not possible to retrieve that info.
    # https://github.com/getmoto/moto/blob/master/moto/wafv2/models.py#L94C10-L94C10


@mock_sts
def test_custom_waf_file_not_found(alias_session):
    runner = CliRunner()
    result = runner.invoke(
        custom_waf,
        ["--app", "app", "--project-profile", "foo", "--svc", "svc", "--env", "env", "--waf-path", "not-a-path"],
    )
    path_string = str(Path(__file__).parent.parent / "not-a-path")

    assert f"File not found...\n{path_string}" in result.output


# No Moto CloudFormation support for AWS::WAFv2::WebACL
@mock_cloudformation
@mock_sts
@patch("commands.waf_cli.check_aws_conn")
@patch("commands.waf_cli.create_stack")
def test_custom_waf_cf_stack_already_exists(create_stack, check_aws_conn, alias_session):
    create_stack.side_effect = boto3.client("cloudformation").exceptions.AlreadyExistsException(
        {"Error": {"Code": 666, "Message": ""}}, "operation name"
    )
    check_aws_conn.return_value = alias_session
    runner = CliRunner()
    result = runner.invoke(
        custom_waf,
        [
            "--app",
            "app",
            "--project-profile",
            "foo",
            "--svc",
            "svc",
            "--env",
            "env",
            "--waf-path",
            "tests/valid_test_waf.yml",
        ],
    )

    assert "CloudFormation Stack already exists" in result.output


def test_custom_waf_delete_in_progress():
    pass


def test_custom_waf():
    pass
