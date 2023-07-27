import os
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
from tests.conftest import TEST_APP_DIR


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
    os.chdir(TEST_APP_DIR)
    runner = CliRunner()
    result = runner.invoke(
        custom_waf,
        ["--app", "app", "--project-profile", "foo", "--svc", "svc", "--env", "env", "--waf-path", "not-a-path"],
    )
    path_string = f"{TEST_APP_DIR}/not-a-path"

    assert f"File not found...\n{path_string}" in result.output
    assert result.exit_code == 0


@mock_cloudformation
@mock_sts
def test_custom_waf_invalid_yml(alias_session):
    os.chdir(TEST_APP_DIR)
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
            "copilot/environments/addons/invalid_cloudformation_template.yml",
        ],
    )
    path_string = str(TEST_APP_DIR / "copilot" / "environments" / "addons" / "invalid_cloudformation_template.yml")

    assert result.exit_code == 0
    assert f"File failed lint check.\n{path_string}" in result.output


# No Moto CloudFormation support for AWS::WAFv2::WebACL
@mock_cloudformation
@mock_sts
@patch("commands.waf_cli.check_aws_conn")
@patch("commands.waf_cli.create_stack")
def test_custom_waf_cf_stack_already_exists(create_stack, check_aws_conn, alias_session):
    os.chdir(TEST_APP_DIR)
    check_aws_conn.return_value = alias_session
    create_stack.side_effect = alias_session.client("cloudformation").exceptions.AlreadyExistsException(
        {"Error": {"Code": 666, "Message": ""}}, "operation name"
    )
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
            "waf.yml",
        ],
    )

    assert "CloudFormation Stack already exists" in result.output
    assert result.exit_code == 0


@mock_cloudformation
@mock_sts
@patch(
    "commands.waf_cli.botocore.client.BaseClient._make_api_call",
    return_value={"Stacks": [{"StackStatus": "DELETE_IN_PROGRESS"}]},
)
@patch("commands.waf_cli.create_stack", return_value={"StackId": "abc", "ResponseMetadata": {"HTTPStatusCode": 200}})
@patch("commands.waf_cli.check_aws_conn")
def test_custom_waf_delete_in_progress(check_aws_conn, create_stack, describe_stacks, alias_session):
    check_aws_conn.return_value = alias_session
    os.chdir(TEST_APP_DIR)
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
            "waf.yml",
        ],
    )

    describe_stacks.assert_called_once_with("DescribeStacks", {"StackName": "abc"})
    assert "Failed to create CloudFormation stack, see AWS webconsole for details" in result.output
    assert result.exit_code == 0


@mock_cloudformation
@mock_ec2
@mock_elbv2
@mock_sts
@mock_wafv2
@patch("commands.waf_cli.get_load_balancer_domain_and_configuration")
@patch("commands.waf_cli.create_stack", return_value={"StackId": "abc", "ResponseMetadata": {"HTTPStatusCode": 200}})
@patch("commands.waf_cli.check_aws_conn")
def test_custom_waf(check_aws_conn, create_stack, get_elastic_load_balancer_domain_and_configuration, alias_session):
    check_aws_conn.return_value = alias_session
    vpc_id = alias_session.client("ec2").create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnet_id = alias_session.client("ec2").create_subnet(VpcId=vpc_id, CidrBlock="10.0.0.0/16")["Subnet"]["SubnetId"]
    elbv2_client = alias_session.client("elbv2")
    lb_arn = elbv2_client.create_load_balancer(Name="foo", Subnets=[subnet_id])["LoadBalancers"][0]["LoadBalancerArn"]
    load_balancer_configuration = elbv2_client.describe_load_balancers(LoadBalancerArns=[lb_arn])["LoadBalancers"][0]
    get_elastic_load_balancer_domain_and_configuration.return_value = (
        "domain-name",
        load_balancer_configuration,
    )
    dns_name = load_balancer_configuration["DNSName"]
    os.chdir(TEST_APP_DIR)
    runner = CliRunner()

    # patching here, to avoid inadvertently mocking the moto test setup calls above, expecting two different boto methods to be called
    with patch(
        "commands.waf_cli.botocore.client.BaseClient._make_api_call",
        side_effect=[
            {"Stacks": [{"StackStatus": "CREATE_COMPLETE", "Outputs": [{"OutputValue": "somekinda-waf:arn"}]}]},
            {"ResponseMetadata": {"HTTPStatusCode": 200}},
        ],
    ) as api_call:
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
                "waf.yml",
            ],
        )

    assert f"WAF created: somekinda-waf:arn" in result.output
    api_call.assert_any_call("DescribeStacks", {"StackName": "abc"})
    api_call.assert_called_with("AssociateWebACL", {"WebACLArn": "somekinda-waf:arn", "ResourceArn": lb_arn})
    assert f"Custom WAF is now associated with {dns_name}" in result.output
    assert result.exit_code == 0
