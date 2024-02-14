from unittest.mock import ANY
from unittest.mock import patch

import boto3
import pytest
from botocore import stub
from botocore.stub import Stubber
from click.testing import CliRunner
from moto import mock_acm
from moto import mock_ec2
from moto import mock_ecs
from moto import mock_elbv2
from moto import mock_sts

from dbt_copilot_helper.commands.dns import InvalidDomainException
from dbt_copilot_helper.commands.dns import add_records
from dbt_copilot_helper.commands.dns import assign
from dbt_copilot_helper.commands.dns import cdn_assign
from dbt_copilot_helper.commands.dns import cdn_delete
from dbt_copilot_helper.commands.dns import cdn_list
from dbt_copilot_helper.commands.dns import configure
from dbt_copilot_helper.commands.dns import copy_records_from_parent_to_subdomain
from dbt_copilot_helper.commands.dns import create_cert
from dbt_copilot_helper.commands.dns import create_hosted_zones
from dbt_copilot_helper.commands.dns import create_required_zones_and_certs
from dbt_copilot_helper.commands.dns import get_base_domain
from dbt_copilot_helper.commands.dns import get_certificate_zone_id
from dbt_copilot_helper.commands.dns import get_required_subdomains
from dbt_copilot_helper.commands.dns import validate_subdomains
from tests.copilot_helper.conftest import mock_aws_client

HYPHENATED_APPLICATION_NAME = "hyphenated-application-name"
ALPHANUMERIC_ENVIRONMENT_NAME = "alphanumericenvironmentname123"
ALPHANUMERIC_SERVICE_NAME = "alphanumericservicename123"
COPILOT_IDENTIFIER = "c0PIlotiD3ntIF3r"
CLUSTER_NAME_SUFFIX = f"Cluster-{COPILOT_IDENTIFIER}"
SERVICE_NAME_SUFFIX = f"Service-{COPILOT_IDENTIFIER}"


def setup_resource_records(route53_session, hosted_zone_id):
    for name, ip in [
        ("dev.uktrade.digital", "192.0.2.10"),
        ("test.dev.uktrade.digital", "192.0.2.20"),
        ("staging.uktrade.digital", "192.0.2.30"),
    ]:
        route53_session.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={
                "Comment": "test",
                "Changes": [
                    {
                        "Action": "CREATE",
                        "ResourceRecordSet": {
                            "Name": name,
                            "Type": "A",
                            "ResourceRecords": [{"Value": ip}],
                            "TTL": 60,
                        },
                    }
                ],
            },
        )


@pytest.mark.parametrize(
    "subdomain, expected_ips, expected_domains",
    [
        ("staging", {"192.0.2.30"}, {"staging.uktrade.digital."}),
        (
            "dev",
            {"192.0.2.10", "192.0.2.20"},
            {"dev.uktrade.digital.", "test.dev.uktrade.digital."},
        ),
    ],
)
def test_copy_records_from_parent_to_subdomain(
    route53_session, subdomain, expected_ips, expected_domains
):
    parent = "uktrade.digital"
    parent_zone_id = route53_session.create_hosted_zone(Name=parent, CallerReference=parent)[
        "HostedZone"
    ]["Id"]
    subdomain = f"{subdomain}.{parent}"
    subdomain_zone_id = route53_session.create_hosted_zone(
        Name=subdomain, CallerReference=subdomain
    )["HostedZone"]["Id"]
    setup_resource_records(route53_session, parent_zone_id)

    with patch("dbt_copilot_helper.commands.dns.add_records") as mock_add_records:
        copy_records_from_parent_to_subdomain(
            route53_session, parent_zone_id, subdomain, subdomain_zone_id
        )

        mock_add_records.assert_called_with(route53_session, ANY, subdomain_zone_id, "UPSERT")
        records_added = [call.args[1] for call in mock_add_records.call_args_list]
        record_ips = {record["ResourceRecords"][0]["Value"] for record in records_added}

        assert {record["Name"] for record in records_added} == expected_domains
        assert record_ips == expected_ips


@patch(
    "dbt_copilot_helper.commands.dns._wait_for_certificate_validation",
    return_value="arn:1234",
)
@patch("click.confirm")
def test_create_cert_with_no_existing_cert_creates_a_cert(
    _wait_for_certificate_validation, mock_click, acm_session, route53_session
):
    resp = route53_session.create_hosted_zone(Name="1234", CallerReference="1234")
    zone_id = resp["HostedZone"]["Id"]

    assert create_cert(acm_session, route53_session, "test.1234", zone_id).startswith(
        "arn:aws:acm:"
    )


@patch(
    "dbt_copilot_helper.commands.dns._wait_for_certificate_validation",
    return_value="arn:1234",
)
def test_create_cert_returns_existing_cert_if_it_is_issued(
    _wait_for_certificate_validation, acm_session, route53_session
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


@pytest.mark.parametrize(
    "zones, expected_id",
    [
        (
            {
                "web.dev.uktrade.digital": "wdud",
                "uktrade.digital": "ud",
                "dev.uktrade.digital": "dud",
            },
            "wdud",
        ),
        ({"prod.uktrade.digital": "pud", "web.prod.uktrade.digital": "wpud"}, "wpud"),
    ],
)
def test_get_certificate_zone_id(zones, expected_id):
    assert get_certificate_zone_id(zones) == expected_id


@patch(
    "dbt_copilot_helper.commands.dns._wait_for_certificate_validation",
    return_value="arn:1234",
)
@patch("click.confirm")
def test_create_cert_deletes_the_old_and_creates_a_new_cert_if_existing_one_is_pending(
    _wait_for_certificate_validation, mock_click, acm_session, route53_session
):
    resp = route53_session.create_hosted_zone(Name="1234", CallerReference="1234")
    zone_id = resp["HostedZone"]["Id"]

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
        actual_cert_arn = create_cert(acm_session, route53_session, domain, zone_id)

        assert new_cert_arn == actual_cert_arn


@patch(
    "dbt_copilot_helper.commands.dns._wait_for_certificate_validation",
    return_value="arn:1234",
)
@patch("click.confirm")
def test_create_cert_with_existing_record_sets_creates_a_cert(
    _wait_for_certificate_validation, mock_click, acm_session, route53_session
):
    resp = route53_session.create_hosted_zone(Name="1234", CallerReference="1234")
    zone_id = resp["HostedZone"]["Id"]

    route53_session.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "_d930b28be6c5927595552b219965053e.test.1234.",
                        "Type": "CNAME",
                        "TTL": 300,
                        "ResourceRecords": [
                            {
                                "Value": "_c9edd76ee4a0e2a74388032f3861cc50.ykybfrwcxw.acm-validations.aws."
                            },
                        ],
                    },
                },
            ],
        },
    )

    assert create_cert(acm_session, route53_session, "test.1234", zone_id).startswith(
        "arn:aws:acm:"
    )


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


@pytest.mark.parametrize(
    "zones_to_delete",
    [
        ["dev.uktrade.digital."],
        ["test.dev.uktrade.digital."],
        ["dev.uktrade.digital.", "test.dev.uktrade.digital."],
    ],
)
@patch("click.confirm")
def test_create_hosted_zones_works_when_base_zone_already_has_records(
    mock_click, route53_session, zones_to_delete
):
    base_domain = "uktrade.digital"
    hz = f"{base_domain}."
    subdomain = "test.dev.uktrade.digital"
    route53_session.create_hosted_zone(Name=hz, CallerReference="base_domain")
    create_hosted_zones(route53_session, base_domain, subdomain)
    zones = {
        hz["Name"]: hz["Id"] for hz in route53_session.list_hosted_zones_by_name()["HostedZones"]
    }
    for zone in zones_to_delete:
        route53_session.delete_hosted_zone(Id=(zones[zone]))

    create_hosted_zones(route53_session, base_domain, subdomain)
    zones = [hz["Name"] for hz in route53_session.list_hosted_zones_by_name()["HostedZones"]]
    assert {"uktrade.digital.", "dev.uktrade.digital.", "test.dev.uktrade.digital."} == set(zones)


@pytest.mark.parametrize(
    "hzs, base_domain, subdomain, expected_zones",
    [
        (
            ["uktrade.digital."],
            "uktrade.digital",
            "dev.uktrade.digital",
            {"uktrade.digital.", "dev.uktrade.digital."},
        ),
        (
            ["uktrade.digital."],
            "uktrade.digital",
            "test.dev.uktrade.digital",
            {"uktrade.digital.", "dev.uktrade.digital.", "test.dev.uktrade.digital."},
        ),
        (
            ["uktrade.digital.", "dev.uktrade.digital."],
            "uktrade.digital",
            "test.dev.uktrade.digital",
            {"uktrade.digital.", "dev.uktrade.digital.", "test.dev.uktrade.digital."},
        ),
        (
            ["uktrade.digital", "prod.uktrade.digital."],
            "prod.uktrade.digital",
            "web.prod.uktrade.digital",
            {"uktrade.digital.", "prod.uktrade.digital.", "web.prod.uktrade.digital."},
        ),
        (
            ["uktrade.digital", "prod.uktrade.digital."],
            "prod.uktrade.digital",
            "v2.web.prod.uktrade.digital",
            {"uktrade.digital.", "prod.uktrade.digital.", "web.prod.uktrade.digital."},
        ),
    ],
)
@patch("click.confirm")
def test_create_hosted_zones_creates_the_correct_hosted_zones(
    mock_click, route53_session, hzs, base_domain, subdomain, expected_zones
):
    for hz in hzs:
        route53_session.create_hosted_zone(Name=hz, CallerReference="uktrade")

    create_hosted_zones(route53_session, base_domain, subdomain)

    zones = {hz["Name"] for hz in route53_session.list_hosted_zones_by_name()["HostedZones"]}

    assert zones == expected_zones


@patch("click.confirm")
def test_create_hosted_zones_is_idempotent(mock_click, route53_session):
    base_domain = "uktrade.digital"
    subdomain = "dev.uktrade.digital"
    route53_session.create_hosted_zone(Name="uktrade.digital.", CallerReference="uktrade-one")

    create_hosted_zones(route53_session, base_domain, subdomain)
    create_hosted_zones(route53_session, base_domain, subdomain)

    zones = [hz["Name"] for hz in route53_session.list_hosted_zones_by_name()["HostedZones"]]

    assert len(zones) == 2
    assert f"{base_domain}." in zones
    assert f"{subdomain}." in zones


@pytest.mark.parametrize(
    "base_domain, domain, zone_dict",
    [
        ("uktrade.digital", "web.dev.uktrade.digital", {"web.dev.uktrade.digital": "wdud"}),
        ("uktrade.digital", "other.web.dev.uktrade.digital", {"web.dev.uktrade.digital": "wdud"}),
        ("prod.uktrade.digital", "web.prod.uktrade.digital", {"web.prod.uktrade.digital": "wpud"}),
        (
            "prod.uktrade.digital",
            "v2.web.prod.uktrade.digital",
            {"web.prod.uktrade.digital": "wpud"},
        ),
    ],
)
@patch(
    "dbt_copilot_helper.commands.dns.create_cert",
    return_value="arn:1234",
)
@patch("click.confirm")
def test_create_required_zones_and_certs(
    mock_create_cert, mock_click, acm_session, route53_session, base_domain, domain, zone_dict
):
    with patch("dbt_copilot_helper.commands.dns.create_hosted_zones") as mock_create_hosted_zones:
        mock_create_hosted_zones.return_value = zone_dict

        route53_session.create_hosted_zone(Name=base_domain, CallerReference="digital")

        response_cert_list = {"CertificateSummaryList": []}

        with Stubber(acm_session) as acm_stub:
            acm_stub.add_response(
                "list_certificates",
                response_cert_list,
                {"CertificateStatuses": stub.ANY, "MaxItems": stub.ANY},
            )
            assert (
                create_required_zones_and_certs(route53_session, acm_session, domain, base_domain)
                == "arn:1234"
            )


@pytest.mark.parametrize("env", ["prod"])
@patch("dbt_copilot_helper.commands.dns.get_aws_session_or_abort")
@patch(
    "dbt_copilot_helper.commands.dns.create_required_zones_and_certs",
    return_value="arn:1234",
)
def test_configure_success(
    mock_create_required_zones_and_certs,
    mock_get_aws_session_or_abort,
    create_test_service_manifest,
    env,
):
    runner = CliRunner()
    result = runner.invoke(
        configure,
        [
            "--project-profile",
            "foo",
            "--env",
            env,
        ],
    )

    expected = [
        "Checking file: copilot/fe/manifest.yml",
        "Domains listed in manifest file",
        f"test-fe.app.prod.uktrade.digital",
        "Checking file: copilot/be/manifest.yml",
        "Domains listed in manifest file",
        f"test-be.app.prod.uktrade.digital",
        "Here are your Certificate ARNs:",
        f"Domain: test-fe.app.prod.uktrade.digital => Cert ARN: arn:1234",
        f"Domain: test-be.app.prod.uktrade.digital => Cert ARN: arn:1234",
    ]

    actual = [line.strip() for line in result.output.split("\n") if line.strip()]
    assert actual == expected


@pytest.mark.parametrize(
    "env, expected_domain_profile",
    [
        ("dev", "dev"),
        ("staging", "dev"),
        ("prod1", "live"),
        ("prod2", "live"),
        ("prod3", "live"),
    ],
)
@patch(
    "dbt_copilot_helper.commands.dns.create_required_zones_and_certs",
    return_value="arn:1234",
)
def test_configure_gets_the_correct_domain_profile(
    mock_create_required_zones_and_certs, create_test_service_manifest, env, expected_domain_profile
):
    with patch("dbt_copilot_helper.commands.dns.get_aws_session_or_abort") as mock_get_session:
        runner = CliRunner()
        result = runner.invoke(
            configure,
            [
                "--project-profile",
                "foo",
                "--env",
                env,
            ],
        )

        actual = [line.strip() for line in result.output.split("\n") if line.strip()]
        mock_get_session.assert_called()
        calls = [call.args[0] for call in mock_get_session.call_args_list]
        assert len(calls) == 2
        assert "foo" in calls
        assert expected_domain_profile in calls


def test_configure_when_copilot_dir_does_not_exist_exits_with_error(fakefs):
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        configure,
        ["--project-profile", "foo", "--env", "dev"],
    )

    assert result.exit_code == 1
    assert "copilot directory appears to be missing" in result.stderr


def test_configure_with_no_manifests_exits_with_error(fakefs):
    fakefs.create_dir("copilot")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(configure, ["--project-profile", "foo", "--env", "dev"])

    assert result.exit_code == 1
    assert "no manifest files were found" in result.stderr


@patch(
    "dbt_copilot_helper.commands.dns.get_aws_session_or_abort",
)
@patch(
    "dbt_copilot_helper.commands.dns.ensure_cwd_is_repo_root",
)
def test_assign(ensure_cwd_is_repo_root, get_aws_session_or_abort):
    client = mock_aws_client(get_aws_session_or_abort)
    client.list_clusters.return_value = {
        "clusterArns": [],
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }

    runner = CliRunner()
    result = runner.invoke(
        assign,
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
    assert (
        "There are no clusters for environment dev of application some-app in AWS account foo"
    ) in result.output


@pytest.mark.parametrize(
    "base_domain, subdomain, exp_subdoms",
    [
        (
            "uktrade.digital",
            "web.dev.uktrade.digital",
            ["dev.uktrade.digital", "web.dev.uktrade.digital"],
        ),
        (
            "uktrade.digital",
            "v2.web.dev.uktrade.digital",
            ["dev.uktrade.digital", "web.dev.uktrade.digital"],
        ),
        ("prod.uktrade.digital", "web.prod.uktrade.digital", ["web.prod.uktrade.digital"]),
        ("prod.uktrade.digital", "v2.web.prod.uktrade.digital", ["web.prod.uktrade.digital"]),
        ("great.gov.uk", "web.great.gov.uk", ["web.great.gov.uk"]),
        ("great.gov.uk", "v2.web.great.gov.uk", ["web.great.gov.uk"]),
    ],
)
def test_get_required_subdomains_returns_the_expected_subdomains(
    base_domain, subdomain, exp_subdoms
):
    subdoms = get_required_subdomains(base_domain, subdomain)

    assert subdoms == exp_subdoms


@pytest.mark.parametrize(
    "domain, subdomain",
    [
        ("uktrade.digital", "www.google.com"),
        ("uktrade.digital", "one.two.uktrade"),
        ("uktrade.digital", "one.two.digital"),
        ("uktrade.digital", "one.two.uktrade.digital.gov.uk"),
        ("uktrade.digital", "one.two-uktrade.digital"),
    ],
)
def test_get_required_subdomains_throws_exception_if_subdomain_and_base_domain_do_not_match(
    domain, subdomain
):
    with pytest.raises(InvalidDomainException, match=f"{subdomain} is not a subdomain of {domain}"):
        get_required_subdomains(domain, subdomain)


def test_get_required_subdomains_throws_exception_if_base_domain_is_not_supported():
    with pytest.raises(InvalidDomainException, match="xyz.com is not a supported base domain"):
        get_required_subdomains("xyz.com", "myapp.xyz.com")


@pytest.mark.parametrize(
    "subdomains, bad_domains",
    [
        (["web.dev.xyz.com"], "web.dev.xyz.com"),
        (
            [
                "web.uktrade.digital",
                "web.dev.xyz.com",
                "v2.web.great.gov.uk",
                "v2.web.trade.gov.uk",
                "v2.web.prod.uktrade.digital",
                "web.dev.bad.url",
            ],
            "web.dev.xyz.com, web.dev.bad.url",
        ),
    ],
)
def test_validate_subdomains_throws_exception_if_its_base_domain_is_not_in_allowed_list(
    subdomains, bad_domains
):
    with pytest.raises(
        InvalidDomainException,
        match=f"The following subdomains do not have one of the allowed base domains: {bad_domains}",
    ):
        validate_subdomains(subdomains)


@pytest.mark.parametrize(
    "subdomains, exp_base_domain",
    [
        (["web.uktrade.digital"], "uktrade.digital"),
        (["v2.web.great.gov.uk"], "great.gov.uk"),
        (["v2.web.trade.gov.uk"], "trade.gov.uk"),
        (["v2.web.prod.uktrade.digital"], "prod.uktrade.digital"),
    ],
)
def test_get_base_domain_success(subdomains, exp_base_domain):
    base_domain = get_base_domain(subdomains)

    assert base_domain == exp_base_domain


def test_get_base_domain_raises_exception_when_multiple_base_domains_found():
    with pytest.raises(
        InvalidDomainException, match="Multiple base domains were found: great.gov.uk, trade.gov.uk"
    ):
        get_base_domain(["v2.web.trade.gov.uk", "v2.web.great.gov.uk"])


def test_get_base_domain_does_not_raise_exception_when_multiple_of_the_same_base_domains_found():
    assert "trade.gov.uk" == get_base_domain(
        ["static.web.trade.gov.uk", "internal.web.trade.gov.uk"]
    )


def test_get_base_domain_raises_exception_when_no_base_domains_found():
    with pytest.raises(
        InvalidDomainException,
        match="No base domains were found for subdomains: v2.web.abc.gov.uk, v2.web.xyz.gov.uk",
    ):
        get_base_domain(["v2.web.xyz.gov.uk", "v2.web.abc.gov.uk"])


@pytest.mark.parametrize(
    "subdomain",
    [
        "web_site.uktrade.digital",
        "web..uktrade.digital",
    ],
)
def test_get_required_subdomains_throws_exception_if_subdomain_is_invalid(subdomain):
    with pytest.raises(
        InvalidDomainException, match=f"Subdomain {subdomain} is not a valid domain"
    ):
        get_required_subdomains("uktrade.digital", subdomain)


def test_get_required_subdomains_throws_exception_with_multiple_errors():
    base_domain = "uktrade.digital"
    subdomain = "subdom..uuktrade.digital"

    with pytest.raises(InvalidDomainException) as exc_info:
        get_required_subdomains(base_domain, subdomain)

    message = exc_info.value.args[0]
    assert f"Subdomain {subdomain} is not a valid domain" in message
    assert f"{subdomain} is not a subdomain of {base_domain}" in message


def setup_alb_listener(conditions, multiple):
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
        Name="foo",
        Subnets=[mocked_subnet_id],
    )["LoadBalancers"][0]["LoadBalancerArn"]
    target_group = mocked_elbv2_client.create_target_group(
        Name="foo", Protocol="HTTPS", Port=80, VpcId=mocked_vpc_id
    )
    target_group_arn = target_group["TargetGroups"][0]["TargetGroupArn"]
    listener_arn = mocked_elbv2_client.create_listener(
        LoadBalancerArn=mocked_load_balancer_arn,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
        Protocol="HTTPS",
    )["Listeners"][0]["ListenerArn"]

    actions = [
        {
            "Type": "forward",
            "TargetGroupArn": target_group_arn,
            "Order": 1,
            "ForwardConfig": {
                "TargetGroups": [{"TargetGroupArn": target_group_arn, "Weight": 1}],
                "TargetGroupStickinessConfig": {"Enabled": False, "DurationSeconds": 3600},
            },
        }
    ]

    mocked_elbv2_client.create_rule(
        ListenerArn=listener_arn,
        Priority=50000,
        Conditions=conditions,
        Actions=actions,
    )
    if multiple:
        mocked_elbv2_client.create_rule(
            ListenerArn=listener_arn,
            Priority=49000,
            Conditions=conditions,
            Actions=actions,
        )

    mocked_ecs_client = session.client("ecs")
    mocked_ecs_client.create_cluster(clusterName=cluster_name)
    mocked_ecs_client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        loadBalancers=[{"loadBalancerName": "foo", "targetGroupArn": target_group_arn}],
    )


@mock_sts
@mock_elbv2
@mock_ec2
@mock_ecs
@mock_acm
def test_cdn_add_if_domain_already_exists(alias_session, aws_credentials):
    conditions = [{"Field": "host-header", "Values": ["test.com"]}]

    setup_alb_listener(conditions, False)

    runner = CliRunner()
    result = runner.invoke(
        cdn_assign,
        [
            "--project-profile",
            "foo",
            "--env",
            ALPHANUMERIC_ENVIRONMENT_NAME,
            "--app",
            HYPHENATED_APPLICATION_NAME,
            "--svc",
            ALPHANUMERIC_SERVICE_NAME,
        ],
        input="test.com",
    )

    assert "Domains currently configured: test.com" in result.output
    assert "test.com already exists, exiting" in result.output


@mock_sts
@mock_elbv2
@mock_ec2
@mock_ecs
@mock_acm
@patch("dbt_copilot_helper.commands.dns.get_aws_session_or_abort", return_value=boto3.Session())
@patch("dbt_copilot_helper.commands.dns.create_required_zones_and_certs", return_value="arn:12345")
def test_cdn_add(alias_session, aws_credentials):
    conditions = [
        {
            "Field": "host-header",
            "Values": ["test.com"],
            "HostHeaderConfig": {"Values": ["test.com"]},
        }
    ]

    setup_alb_listener(conditions, False)

    runner = CliRunner()
    result = runner.invoke(
        cdn_assign,
        [
            "--project-profile",
            "foo",
            "--env",
            ALPHANUMERIC_ENVIRONMENT_NAME,
            "--app",
            HYPHENATED_APPLICATION_NAME,
            "--svc",
            ALPHANUMERIC_SERVICE_NAME,
        ],
        input="web.dev.uktrade.digital",
    )

    assert "Domains now configured: ['test.com', 'web.dev.uktrade.digital']" in result.output


@mock_sts
@mock_elbv2
@mock_ec2
@mock_ecs
@mock_acm
@patch("dbt_copilot_helper.commands.dns.get_aws_session_or_abort", return_value=boto3.Session())
@patch("dbt_copilot_helper.commands.dns.create_required_zones_and_certs", return_value="arn:12345")
def test_cdn_delete(alias_session, aws_credentials):
    conditions = [
        {
            "Field": "host-header",
            "Values": ["test.com", "web.dev.uktrade.digital"],
            "HostHeaderConfig": {"Values": ["test.com", "web.dev.uktrade.digital"]},
        }
    ]

    setup_alb_listener(conditions, False)

    runner = CliRunner()
    result = runner.invoke(
        cdn_delete,
        [
            "--project-profile",
            "foo",
            "--env",
            ALPHANUMERIC_ENVIRONMENT_NAME,
            "--app",
            HYPHENATED_APPLICATION_NAME,
            "--svc",
            ALPHANUMERIC_SERVICE_NAME,
        ],
        input="web.dev.uktrade.digital\ny\n",
    )
    assert "deleting web.dev.uktrade.digital\nDomains now configured: ['test.com']" in result.output


@mock_sts
@mock_elbv2
@mock_ec2
@mock_ecs
@mock_acm
def test_cdn_list(alias_session, aws_credentials):
    conditions = [
        {
            "Field": "host-header",
            "Values": ["test.com", "web.dev.uktrade.digital"],
            "HostHeaderConfig": {"Values": ["test.com", "web.dev.uktrade.digital"]},
        }
    ]

    setup_alb_listener(conditions, False)

    runner = CliRunner()
    result = runner.invoke(
        cdn_list,
        [
            "--project-profile",
            "foo",
            "--env",
            ALPHANUMERIC_ENVIRONMENT_NAME,
            "--app",
            HYPHENATED_APPLICATION_NAME,
            "--svc",
            ALPHANUMERIC_SERVICE_NAME,
        ],
    )
    assert "Domains currently configured: ['test.com', 'web.dev.uktrade.digital']" in result.output


@mock_sts
@mock_elbv2
@mock_ec2
@mock_ecs
@mock_acm
@patch("dbt_copilot_helper.commands.dns.get_aws_session_or_abort", return_value=boto3.Session())
@patch("dbt_copilot_helper.commands.dns.create_required_zones_and_certs", return_value="arn:12345")
def test_cdn_add_multiple_domains(alias_session, aws_credentials):
    conditions = [
        {
            "Field": "host-header",
            "Values": ["test.com"],
            "HostHeaderConfig": {"Values": ["test.com"]},
        }
    ]

    setup_alb_listener(conditions, True)

    runner = CliRunner()
    result = runner.invoke(
        cdn_assign,
        [
            "--project-profile",
            "foo",
            "--env",
            ALPHANUMERIC_ENVIRONMENT_NAME,
            "--app",
            HYPHENATED_APPLICATION_NAME,
            "--svc",
            ALPHANUMERIC_SERVICE_NAME,
        ],
        input="web.dev.uktrade.digital\nweb2.dev.uktrade.digital\n",
    )
    assert "Domains now configured: ['test.com', 'web.dev.uktrade.digital']" in result.output
    assert "Domains now configured: ['test.com', 'web2.dev.uktrade.digital']" in result.output
