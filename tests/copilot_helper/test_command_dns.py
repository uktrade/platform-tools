import json
from unittest.mock import mock_open
from unittest.mock import patch

import boto3
import pytest
from botocore import stub
from botocore.stub import Stubber
from click.testing import CliRunner
from moto import mock_ec2
from moto import mock_ecs
from moto import mock_elbv2

from dbt_copilot_helper.commands.dns import add_records
from dbt_copilot_helper.commands.dns import assign_domain
from dbt_copilot_helper.commands.dns import check_for_records
from dbt_copilot_helper.commands.dns import check_r53
from dbt_copilot_helper.commands.dns import configure_domain
from dbt_copilot_helper.commands.dns import create_cert
from dbt_copilot_helper.commands.dns import create_hosted_zone
from dbt_copilot_helper.commands.dns import get_load_balancer_domain_and_configuration

HYPHENATED_APPLICATION_NAME = "hyphenated-application-name"
ALPHANUMERIC_ENVIRONMENT_NAME = "alphanumericenvironmentname123"
ALPHANUMERIC_SERVICE_NAME = "alphanumericservicename123"
COPILOT_IDENTIFIER = "c0PIlotiD3ntIF3r"
CLUSTER_NAME_SUFFIX = f"Cluster-{COPILOT_IDENTIFIER}"
SERVICE_NAME_SUFFIX = f"Service-{COPILOT_IDENTIFIER}"


def test_check_for_records(route53_session):
    response = route53_session.create_hosted_zone(Name="1234", CallerReference="1234")
    assert (
        check_for_records(
            route53_session, response["HostedZone"]["Id"], "test.1234", response["HostedZone"]["Id"]
        )
        == True
    )


@patch(
    "dbt_copilot_helper.commands.dns._wait_for_certificate_validation",
    return_value="arn:1234",
)
@patch("click.confirm")
def test_create_cert_with_no_existing_cert_creates_a_cert(
    _wait_for_certificate_validation, mock_click, acm_session, route53_session
):
    route53_session.create_hosted_zone(Name="1234", CallerReference="1234")

    assert create_cert(acm_session, route53_session, "test.1234", 1).startswith("arn:aws:acm:")


@patch(
    "dbt_copilot_helper.commands.dns._wait_for_certificate_validation",
    return_value="arn:1234",
)
@patch("click.confirm")
def test_create_cert_returns_existing_cert_if_it_is_issued(
    _wait_for_certificate_validation, mock_click, acm_session, route53_session
):
    route53_session.create_hosted_zone(Name="1234", CallerReference="1234")

    existing_cert_arn = "arn:aws:acm:eu-west-2:abc1234:certificate/ca88age-f10a-1eaf"
    response_cert_list = {
        "CertificateSummaryList": [
            {
                "CertificateArn": existing_cert_arn,
                "DomainName": "test.1234",
                "SubjectAlternativeNameSummaries": ["v2.demodjango.john.uktrade.digital"],
                "Status": "ISSUED",
                "InUse": True,
                "RenewalEligibility": "ELIGIBLE",
            }
        ]
    }

    with Stubber(acm_session) as acm_stub:
        acm_stub.add_response(
            "list_certificates",
            response_cert_list,
            {"CertificateStatuses": stub.ANY, "MaxItems": stub.ANY},
        )
        assert existing_cert_arn == create_cert(acm_session, route53_session, "test.1234", 1)


@patch(
    "dbt_copilot_helper.commands.dns._wait_for_certificate_validation",
    return_value="arn:1234",
)
@patch("click.confirm")
def test_create_cert_deletes_the_old_and_creates_a_new_cert_if_existing_one_is_pending(
    _wait_for_certificate_validation, mock_click, acm_session, route53_session
):
    route53_session.create_hosted_zone(Name="1234", CallerReference="1234")

    domain = "test.1234"
    old_cert_arn = "arn:aws:acm:eu-west-2:abc1234:certificate/ca88age-f10a-1eaf"
    response_cert_list = {
        "CertificateSummaryList": [
            {
                "CertificateArn": old_cert_arn,
                "DomainName": domain,
                "SubjectAlternativeNameSummaries": ["v2.demodjango.john.uktrade.digital"],
                "Status": "PENDING_VALIDATION",
                "InUse": True,
                "RenewalEligibility": "ELIGIBLE",
            }
        ]
    }

    cert_desc_response = {
        "Certificate": {
            "DomainValidationOptions": [
                {
                    "DomainName": domain,
                    "ResourceRecord": {
                        "Name": "some-acm-name.1234",
                        "Value": "some-acm-value",
                        "Type": "CNAME",
                    },
                },
            ],
        }
    }

    new_cert_arn = "arn:aws:acm:eu-west-2:abc1234:certificate/something-n3w"

    with Stubber(acm_session) as acm_stub:
        acm_stub.add_response(
            "list_certificates",
            response_cert_list,
            {"CertificateStatuses": stub.ANY, "MaxItems": stub.ANY},
        )
        acm_stub.add_response(
            "delete_certificate",
            {},
            {"CertificateArn": old_cert_arn},
        )
        acm_stub.add_response(
            "request_certificate",
            {"CertificateArn": new_cert_arn},
            {"DomainName": domain, "ValidationMethod": "DNS"},
        )
        acm_stub.add_response(
            "describe_certificate", cert_desc_response, {"CertificateArn": new_cert_arn}
        )
        actual_cert_arn = create_cert(acm_session, route53_session, domain, 1)

        assert new_cert_arn == actual_cert_arn


def test_add_records(route53_session):
    response = route53_session.create_hosted_zone(Name="1234", CallerReference="1234")

    route53_session.change_resource_record_sets(
        HostedZoneId=response["HostedZone"]["Id"],
        ChangeBatch={
            "Comment": "test",
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "test.1234",
                        "Type": "A",
                        "ResourceRecords": [
                            {
                                "Value": "192.0.2.45",
                            },
                        ],
                        "TTL": 60,
                    },
                }
            ],
        },
    )

    record = {
        "Name": "test.1234",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "recod.stuff"}],
    }

    assert add_records(route53_session, record, response["HostedZone"]["Id"], "CREATE") == "INSYNC"


@patch("click.confirm")
def test_create_hosted_zone(mock_click, route53_session):
    route53_session.create_hosted_zone(Name="1234", CallerReference="1234")

    assert create_hosted_zone(route53_session, "test.test.1234", "test.1234", 1)


@pytest.mark.parametrize(
    "zones_to_delete",
    [
        ["test.1234."],
        ["test.test.1234."],
        ["test.1234.", "test.test.1234."],
    ],
)
@patch("click.confirm")
def test_create_records_works_when_base_zone_already_has_records(
    mock_click, route53_session, zones_to_delete
):
    route53_session.create_hosted_zone(Name="1234.", CallerReference="1234")
    create_hosted_zone(route53_session, "test.test.1234", "test.1234", 1)
    zones = {
        hz["Name"]: hz["Id"] for hz in route53_session.list_hosted_zones_by_name()["HostedZones"]
    }
    for zone in zones_to_delete:
        route53_session.delete_hosted_zone(Id=(zones[zone]))

    assert create_hosted_zone(route53_session, "test.test.1234", "test.1234", 1)
    zones = [hz["Name"] for hz in route53_session.list_hosted_zones_by_name()["HostedZones"]]
    assert "test.test.1234." in zones
    assert "test.1234." in zones


# Listcertificates is not implementaed in moto acm. Neeed to patch it
@patch(
    "dbt_copilot_helper.commands.dns.create_cert",
    return_value="arn:1234",
)
def test_check_r53(create_cert, route53_session):
    session = boto3.session.Session(profile_name="foo")
    route53_session.create_hosted_zone(Name="test.1234", CallerReference="1234")

    assert check_r53(session, session, "test.test.1234", "test.1234") == "arn:1234"


@patch(
    "dbt_copilot_helper.commands.dns.check_and_return_aws_session",
)
@patch(
    "dbt_copilot_helper.commands.dns.check_r53",
    return_value="arn:1234",
)
def test_configure_domain(check_and_return_aws_session, check_r53, fakefs):
    fakefs.create_file(
        "copilot/manifest.yml",
        contents="""
environments:
  dev:
    http:
      alias: v2.app.dev.test.1234

  staging:
    http:
      alias: v2.app.staging.test.12345
""",
    )

    runner = CliRunner()
    result = runner.invoke(
        configure_domain,
        ["--domain-profile", "dev", "--project-profile", "foo", "--base-domain", "test.1234"],
    )
    expected = "Checking file: copilot/manifest.yml\nDomains listed in manifest file\n\nEnvironment: dev => Domain: v2.app.dev.test.1234\n\nEnvironment: staging => Domain: v2.app.staging.test.12345\n\nHere are your Certificate ARNs:\nDomain: v2.app.dev.test.1234\t => Cert ARN: arn:1234\nDomain: v2.app.staging.test.12345\t => Cert ARN: arn:1234\n"

    assert result.output == expected


@patch(
    "dbt_copilot_helper.commands.dns.check_and_return_aws_session",
)
@patch(
    "dbt_copilot_helper.commands.dns.check_r53",
    return_value="arn:1234",
)
def test_configure_domain_env_flag(check_and_return_aws_session, check_r53, fakefs):
    fakefs.create_file(
        "copilot/manifest.yml",
        contents="""
environments:
  dev:
    http:
      alias: v2.app.dev.test.1234

  staging:
    http:
      alias: v2.app.staging.test.12345
      
  prod:
    http:
      alias: v2.app.prod.test.12345
""",
    )

    runner = CliRunner()
    result = runner.invoke(
        configure_domain,
        [
            "--domain-profile",
            "dev",
            "--project-profile",
            "foo",
            "--base-domain",
            "test.1234",
            "--env",
            "dev",
        ],
    )

    expected = "Checking file: copilot/manifest.yml\nDomains listed in manifest file\n\nEnvironment: dev => Domain: v2.app.dev.test.1234\n\nHere are your Certificate ARNs:\nDomain: v2.app.dev.test.1234\t => Cert ARN: arn:1234\n"

    # Check calls to check_r53
    # Check calls to check_and_return_aws_session

    assert result.output == expected


def test_configure_domain_copilot_dir_does_not_exist_exits_with_error(fakefs):
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        configure_domain,
        [
            "--domain-profile",
            "dev",
            "--project-profile",
            "foo",
            "--base-domain",
            "test.1234",
            "--env",
            "dev",
        ],
    )

    assert result.exit_code == 1
    assert "copilot directory appears to be missing" in result.stderr


def test_configure_domain_no_manifests_exits_with_error(fakefs):
    fakefs.create_dir("copilot")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        configure_domain,
        [
            "--domain-profile",
            "dev",
            "--project-profile",
            "foo",
            "--base-domain",
            "test.1234",
            "--env",
            "dev",
        ],
    )

    assert result.exit_code == 1
    assert "no manifest files were found" in result.stderr


@patch(
    "dbt_copilot_helper.commands.dns.check_and_return_aws_session",
)
@patch(
    "dbt_copilot_helper.commands.dns.check_r53",
    return_value="arn:1234",
)
def test_configure_domain_live_domain_profile(check_and_return_aws_session, check_r53, fakefs):
    fakefs.create_file(
        "copilot/manifest.yml",
        contents="""
environments:
  dev:
    http:
      alias: v2.app.dev.test.1234

  prod:
    http:
      alias: v2.app.prod.test.12345
""",
    )

    runner = CliRunner()
    result = runner.invoke(
        configure_domain,
        ["--domain-profile", "live", "--project-profile", "foo", "--base-domain", "test.1234"],
    )
    expected = "Checking file: copilot/manifest.yml\nDomains listed in manifest file\n\nEnvironment: prod => Domain: v2.app.prod.test.12345\n\nHere are your Certificate ARNs:\nDomain: v2.app.prod.test.12345\t => Cert ARN: arn:1234\n"

    assert result.output == expected


@patch(
    "dbt_copilot_helper.commands.dns.check_and_return_aws_session",
)
@patch("dbt_copilot_helper.commands.dns.check_response", return_value="{}")
@patch(
    "dbt_copilot_helper.commands.dns.ensure_cwd_is_repo_root",
)
def test_assign_domain(check_and_return_aws_session, check_response, ensure_cwd_is_repo_root):
    runner = CliRunner()
    result = runner.invoke(
        assign_domain,
        [
            "--app",
            "some-app",
            "--domain-profile",
            "dev",
            "--project-profile",
            "foo",
            "--svc",
            "web",
            "--env",
            "dev",
        ],
    )
    assert result.output.startswith("There are no clusters matching")


@mock_ecs
def test_get_load_balancer_domain_and_configuration_no_clusters(capfd):
    with pytest.raises(SystemExit):
        get_load_balancer_domain_and_configuration(
            boto3.Session(),
            HYPHENATED_APPLICATION_NAME,
            ALPHANUMERIC_ENVIRONMENT_NAME,
            ALPHANUMERIC_SERVICE_NAME,
        )

    out, _ = capfd.readouterr()

    assert (
        out == f"There are no clusters matching {HYPHENATED_APPLICATION_NAME} in this AWS account\n"
    )


@mock_ecs
def test_get_load_balancer_domain_and_configuration_no_services(capfd):
    boto3.Session().client("ecs").create_cluster(
        clusterName=f"{HYPHENATED_APPLICATION_NAME}-{ALPHANUMERIC_ENVIRONMENT_NAME}-{CLUSTER_NAME_SUFFIX}"
    )
    with pytest.raises(SystemExit):
        get_load_balancer_domain_and_configuration(
            boto3.Session(),
            HYPHENATED_APPLICATION_NAME,
            ALPHANUMERIC_SERVICE_NAME,
            ALPHANUMERIC_ENVIRONMENT_NAME,
        )

    out, _ = capfd.readouterr()

    assert (
        out == f"There are no services matching {ALPHANUMERIC_SERVICE_NAME} in this aws account\n"
    )


@mock_elbv2
@mock_ec2
@mock_ecs
def test_get_load_balancer_domain_and_configuration(tmp_path):
    cluster_name = (
        f"{HYPHENATED_APPLICATION_NAME}-{ALPHANUMERIC_ENVIRONMENT_NAME}-{CLUSTER_NAME_SUFFIX}"
    )
    service_name = f"{HYPHENATED_APPLICATION_NAME}-{ALPHANUMERIC_ENVIRONMENT_NAME}-{ALPHANUMERIC_SERVICE_NAME}-{SERVICE_NAME_SUFFIX}"
    session = boto3.Session()
    mocked_vpc_id = session.client("ec2").create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    mocked_subnet_id = session.client("ec2").create_subnet(
        VpcId=mocked_vpc_id, CidrBlock="10.0.0.0/16"
    )["Subnet"]["SubnetId"]
    mocked_elbv2_client = session.client("elbv2")
    mocked_load_balancer_arn = mocked_elbv2_client.create_load_balancer(
        Name="foo", Subnets=[mocked_subnet_id]
    )["LoadBalancers"][0]["LoadBalancerArn"]
    target_group = mocked_elbv2_client.create_target_group(
        Name="foo", Protocol="HTTPS", Port=80, VpcId=mocked_vpc_id
    )
    target_group_arn = target_group["TargetGroups"][0]["TargetGroupArn"]
    mocked_elbv2_client.create_listener(
        LoadBalancerArn=mocked_load_balancer_arn,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )
    mocked_ecs_client = session.client("ecs")
    mocked_ecs_client.create_cluster(clusterName=cluster_name)
    mocked_ecs_client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        loadBalancers=[{"loadBalancerName": "foo", "targetGroupArn": target_group_arn}],
    )
    mocked_service_manifest_contents = {
        "environments": {ALPHANUMERIC_ENVIRONMENT_NAME: {"http": {"alias": "somedomain.tld"}}}
    }
    open_mock = mock_open(read_data=json.dumps(mocked_service_manifest_contents))

    with patch("dbt_copilot_helper.commands.dns.open", open_mock):
        domain_name, load_balancer_configuration = get_load_balancer_domain_and_configuration(
            boto3.Session(),
            HYPHENATED_APPLICATION_NAME,
            ALPHANUMERIC_SERVICE_NAME,
            ALPHANUMERIC_ENVIRONMENT_NAME,
        )

    open_mock.assert_called_once_with(f"./copilot/{ALPHANUMERIC_SERVICE_NAME}/manifest.yml", "r")
    assert domain_name == "somedomain.tld"
    assert load_balancer_configuration["LoadBalancerArn"] == mocked_load_balancer_arn
    assert load_balancer_configuration["LoadBalancerName"] == "foo"
    assert load_balancer_configuration["VpcId"] == mocked_vpc_id
    assert load_balancer_configuration["AvailabilityZones"][0]["SubnetId"] == mocked_subnet_id
