from unittest.mock import MagicMock
from unittest.mock import patch

import boto3
import click
import pytest
from moto import mock_aws

from dbt_platform_helper.domain.copilot_environment import CertificateNotFoundException
from dbt_platform_helper.domain.copilot_environment import find_https_certificate
from dbt_platform_helper.domain.copilot_environment import get_cert_arn
from dbt_platform_helper.domain.copilot_environment import get_subnet_ids
from dbt_platform_helper.domain.copilot_environment import get_vpc_id


@pytest.mark.parametrize("vpc_name", ["default", "default-prod"])
@mock_aws
def test_get_vpc_id(vpc_name):
    session = boto3.session.Session()
    vpc = create_moto_mocked_vpc(session, vpc_name)
    expected_vpc_id = vpc["VpcId"]

    actual_vpc_id = get_vpc_id(session, "prod")

    assert expected_vpc_id == actual_vpc_id

    vpc_id_from_name = get_vpc_id(session, "not-an-env", vpc_name=vpc_name)

    assert expected_vpc_id == vpc_id_from_name


@mock_aws
def test_get_vpc_id_failure(capsys):

    with pytest.raises(click.Abort):
        get_vpc_id(boto3.session.Session(), "development")

    captured = capsys.readouterr()

    assert "No VPC found with name default-development in AWS account default." in captured.out


@mock_aws
def test_get_subnet_ids():
    session = boto3.session.Session()
    vpc_id = create_moto_mocked_vpc(session, "default-development")["VpcId"]
    expected_public_subnet_id = create_moto_mocked_subnet(
        session, vpc_id, "public", "10.0.128.0/24"
    )
    expected_private_subnet_id = create_moto_mocked_subnet(
        session, vpc_id, "private", "10.0.1.0/24"
    )

    public_subnet_ids, private_subnet_ids = get_subnet_ids(
        session, vpc_id, "environment-name-does-not-matter"
    )

    assert public_subnet_ids == [expected_public_subnet_id]
    assert private_subnet_ids == [expected_private_subnet_id]


@mock_aws
def test_get_subnet_ids_with_cloudformation_export_returning_a_different_order():
    # This test and the associated behavior can be removed when we stop using AWS Copilot to deploy the services
    def _list_exports_subnet_object(environment: str, subnet_ids: list[str], visibility: str):
        return {
            "Name": f"application-{environment}-{visibility.capitalize()}Subnets",
            "Value": f"{','.join(subnet_ids)}",
        }

    def _describe_subnets_subnet_object(subnet_id: str, visibility: str):
        return {
            "SubnetId": subnet_id,
            "Tags": [{"Key": "subnet_type", "Value": visibility}],
        }

    def _non_subnet_exports(number):
        return [
            {
                "Name": f"application-environment-NotASubnet",
                "Value": "does-not-matter",
            }
        ] * number

    expected_public_subnet_id_1 = "subnet-1public"
    expected_public_subnet_id_2 = "subnet-2public"
    expected_private_subnet_id_1 = "subnet-1private"
    expected_private_subnet_id_2 = "subnet-2private"

    mock_boto3_session = MagicMock()

    # Cloudformation list_exports returns a paginated response with the exports in the expected order plus some we are not interested in
    mock_boto3_session.client("cloudformation").get_paginator(
        "list_exports"
    ).paginate.return_value = [
        {"Exports": _non_subnet_exports(5)},
        {
            "Exports": [
                _list_exports_subnet_object(
                    "environment",
                    [
                        expected_public_subnet_id_1,
                        expected_public_subnet_id_2,
                    ],
                    "public",
                ),
                _list_exports_subnet_object(
                    "environment",
                    [
                        expected_private_subnet_id_1,
                        expected_private_subnet_id_2,
                    ],
                    "private",
                ),
                _list_exports_subnet_object(
                    "otherenvironment",
                    [expected_public_subnet_id_1],
                    "public",
                ),
                _list_exports_subnet_object(
                    "otherenvironment",
                    [expected_private_subnet_id_2],
                    "private",
                ),
            ]
        },
        {"Exports": _non_subnet_exports(5)},
    ]

    # EC2 client should return them in an order that differs from the CloudFormation Export
    mock_boto3_session.client("ec2").describe_subnets.return_value = {
        "Subnets": [
            _describe_subnets_subnet_object(expected_public_subnet_id_2, "public"),
            _describe_subnets_subnet_object(expected_public_subnet_id_1, "public"),
            _describe_subnets_subnet_object(expected_private_subnet_id_2, "private"),
            _describe_subnets_subnet_object(expected_private_subnet_id_1, "private"),
        ]
    }

    # Act (there's a lot of setup, worth signposting where this happens)
    public_subnet_ids, private_subnet_ids = get_subnet_ids(
        mock_boto3_session, "vpc-id-does-not-matter", "environment"
    )

    assert public_subnet_ids == [
        expected_public_subnet_id_1,
        expected_public_subnet_id_2,
    ]
    assert private_subnet_ids == [
        expected_private_subnet_id_1,
        expected_private_subnet_id_2,
    ]


@mock_aws
def test_get_subnet_ids_failure(capsys):

    with pytest.raises(click.Abort):
        get_subnet_ids(boto3.session.Session(), "123", "environment-name-does-not-matter")

    captured = capsys.readouterr()

    assert "No subnets found for VPC with id: 123." in captured.out


@mock_aws
@patch(
    "dbt_platform_helper.domain.copilot_environment.find_https_certificate",
    return_value="CertificateArn",
)
def test_get_cert_arn(find_https_certificate):

    session = boto3.session.Session()
    actual_arn = get_cert_arn(session, "test-application", "development")

    assert "CertificateArn" == actual_arn


@mock_aws
def test_cert_arn_failure(capsys):

    session = boto3.session.Session()

    with pytest.raises(click.Abort):
        get_cert_arn(session, "test-application", "development")

    captured = capsys.readouterr()

    assert "No certificate found with domain name matching environment development." in captured.out


def create_moto_mocked_subnet(session, vpc_id, visibility, cidr_block):
    return session.client("ec2").create_subnet(
        CidrBlock=cidr_block,
        VpcId=vpc_id,
        TagSpecifications=[
            {
                "ResourceType": "subnet",
                "Tags": [
                    {"Key": "subnet_type", "Value": visibility},
                ],
            },
        ],
    )["Subnet"]["SubnetId"]


def create_moto_mocked_vpc(session, vpc_name):
    vpc = session.client("ec2").create_vpc(
        CidrBlock="10.0.0.0/16",
        TagSpecifications=[
            {
                "ResourceType": "vpc",
                "Tags": [
                    {"Key": "Name", "Value": vpc_name},
                ],
            },
        ],
    )["Vpc"]
    return vpc


class TestFindHTTPSCertificate:
    @patch(
        "dbt_platform_helper.domain.copilot_environment.find_https_listener",
        return_value="https_listener_arn",
    )
    def test_when_no_certificate_present(self, mock_find_https_listener):
        boto_mock = MagicMock()
        boto_mock.client().describe_listener_certificates.return_value = {"Certificates": []}

        with pytest.raises(CertificateNotFoundException):
            find_https_certificate(boto_mock, "test-application", "development")

    @patch(
        "dbt_platform_helper.domain.copilot_environment.find_https_listener",
        return_value="https_listener_arn",
    )
    def test_when_single_https_certificate_present(self, mock_find_https_listener):
        boto_mock = MagicMock()
        boto_mock.client().describe_listener_certificates.return_value = {
            "Certificates": [{"CertificateArn": "certificate_arn", "IsDefault": "True"}]
        }

        certificate_arn = find_https_certificate(boto_mock, "test-application", "development")
        assert "certificate_arn" == certificate_arn

    @patch(
        "dbt_platform_helper.domain.copilot_environment.find_https_listener",
        return_value="https_listener_arn",
    )
    def test_when_multiple_https_certificate_present(self, mock_find_https_listener):
        boto_mock = MagicMock()
        boto_mock.client().describe_listener_certificates.return_value = {
            "Certificates": [
                {"CertificateArn": "certificate_arn_default", "IsDefault": "True"},
                {"CertificateArn": "certificate_arn_not_default", "IsDefault": "False"},
            ]
        }

        certificate_arn = find_https_certificate(boto_mock, "test-application", "development")
        assert "certificate_arn_default" == certificate_arn
