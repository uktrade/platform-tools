import os
from pathlib import Path
from unittest.mock import patch

import boto3
from botocore.stub import Stubber
import pytest
from click.testing import CliRunner
from moto import mock_acm
from moto import mock_route53

from commands.dns_cli import add_records, check_for_records, create_hosted_zone, check_r53, create_cert
from utils.aws import check_aws_conn

@pytest.fixture(scope='module')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    moto_credentials_file_path = Path(__file__).parent.absolute() / 'dummy_aws_credentials'
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = str(moto_credentials_file_path)

# Not much value in testing these while moto doesn't support `describe_certificate`, `list_certificates`
def test_wait_for_certificate_validation():
    ...

# Cant test list_certificate, describe_certificate as not supported

   
# @mock_acm
# @mock_route53
# def test_create_cert(aws_credentials):
#     session = boto3.session.Session(profile_name="foo")   
#     client = session.client("acm", region_name="eu-west-2") 
#     client2 = session.client("route53")
 
@mock_route53
def test_check_for_records(aws_credentials):
    session = boto3.session.Session(profile_name="foo")
    client = session.client("route53")

    response =  client.create_hosted_zone(Name='1234', CallerReference='1234')

    #breakpoint()
    # client.list_resource_record_sets(
    #     HostedZoneId=response['HostedZone']['Id'],
    # )

    record = {
                "Name": "test.1234",
                "Type": "CNAME",
                "TTL": 300,
                "ResourceRecords": [{"Value": "recod.stuff"}],
            }
    
    assert check_for_records(client, response['HostedZone']['Id'], "test.1234", response['HostedZone']['Id']) == True


@patch(
        "commands.dns_cli.wait_for_certificate_validation",
        return_value="arn:1234",
)
@mock_acm
@mock_route53
@patch("click.confirm")
def test_create_cert(wait_for_certificate_validation, mock_click):
    session = boto3.session.Session(profile_name="foo", region_name="eu-west-2")
    domain_session = boto3.session.Session(profile_name="bar")
    client = session.client("acm")
    stubber = Stubber(client)
    domain_client = domain_session.client("route53")
    # breakpoint()

    response =  domain_client.create_hosted_zone(Name='1234', CallerReference='1234')

    response_desc = {
                'Certificate': {
                    'CertificateArn': 'arn:1234567890123456789',
                    'DomainName': 'test.1234',
                    'DomainValidationOptions': [
                        {
                            'DomainName': 'test.1234',
                            'ValidationStatus': 'SUCCESS',
                            'ResourceRecord': {
                                'Name': 'test.record',
                                'Type': 'CNAME',
                                'Value': 'pointing.to.this'
                            },
                            'ValidationMethod': 'DNS'
                        },
                    ],
                }
            }
    expected_params = {'CertificateArn': 'arn:1234567890123456789'}
    stubber.add_response('describe_certificate', response_desc, expected_params)
    with stubber:
        response = client.describe_certificate(CertificateArn='arn:1234567890123456789')
  
    assert create_cert(client, domain_client, "test.1234", 1).startswith("arn:aws:acm:") == True


@mock_route53
def test_add_records():
    session = boto3.session.Session(profile_name="foo")
    client = session.client("route53")
    
    response =  client.create_hosted_zone(Name='1234', CallerReference='1234')

    #breakpoint()
    client.change_resource_record_sets(
        HostedZoneId=response['HostedZone']['Id'],
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
                            'TTL': 60,
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
    
    assert add_records(client, record , response['HostedZone']['Id'],"CREATE") == "INSYNC"



@mock_route53
@patch("click.confirm")
def test_create_hosted_zone(mock_click):
    session = boto3.session.Session(profile_name="foo")
    client = session.client("route53")

    mock_click.return_value = "y"
    client.create_hosted_zone(Name='1234', CallerReference='1234')

    # client.list_hosted_zones_by_name()

    assert create_hosted_zone(client, "test.test.1234", "test.1234", 1) == True


# Listcertificates is not implementaed in moto acm. Neeed to patch it
@patch(
        "commands.dns_cli.create_cert",
        return_value="arn:1234",
)
@mock_route53
def test_check_r53(create_cert):
    session = boto3.session.Session(profile_name="foo")
    client = session.client("route53")

    client.create_hosted_zone(Name='test.1234', CallerReference='1234')


    assert check_r53(session, session, "test.test.1234", "test.1234") == "arn:1234"

     