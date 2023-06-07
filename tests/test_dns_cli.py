import os
from pathlib import Path
from unittest.mock import patch

import boto3
from botocore.stub import Stubber
import pytest
from click.testing import CliRunner
from moto import mock_acm
from moto import mock_route53
from moto import mock_iam

from commands.dns_cli import add_records, check_for_records, create_hosted_zone, check_r53, create_cert, check_domain, assign_domain


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    moto_credentials_file_path = Path(__file__).parent.absolute() / 'dummy_aws_credentials'
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = str(moto_credentials_file_path)


@pytest.fixture(scope="function")
def acm_session(aws_credentials):
    with mock_acm():
        session = boto3.session.Session(profile_name="foo", region_name="eu-west-2")
        yield session.client("acm")


@pytest.fixture(scope="function")
def route53_session(aws_credentials):
    with mock_route53():
        session = boto3.session.Session(profile_name="foo", region_name="eu-west-2")
        yield session.client("route53")


@pytest.fixture(scope="function")
def iam_session(aws_credentials):
    with mock_iam():
        session = boto3.session.Session(profile_name="foo", region_name="eu-west-2")
        yield session.client("iam")


# Not much value in testing these while moto doesn't support `describe_certificate`, `list_certificates`
def test_wait_for_certificate_validation():
    ...

 
def test_check_for_records(route53_session):
    response =  route53_session.create_hosted_zone(Name='1234', CallerReference='1234')  
    assert check_for_records(route53_session, response['HostedZone']['Id'], "test.1234", response['HostedZone']['Id']) == True


@patch(
        "commands.dns_cli.wait_for_certificate_validation",
        return_value="arn:1234",
)
@patch("click.confirm")
def test_create_cert(wait_for_certificate_validation, mock_click, acm_session, route53_session):
    stubber = Stubber(acm_session)
    route53_session.create_hosted_zone(Name='1234', CallerReference='1234')

    response_desc = {
                'Certificate': {
                    'CertificateArn': 'arn:1234567890123456789',
                    'DomainName': 'test.domain',
                    'DomainValidationOptions': [
                        {
                            'DomainName': 'test.domain',
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
        acm_session.describe_certificate(CertificateArn='arn:1234567890123456789')
  
    assert create_cert(acm_session, route53_session, "test.1234", 1).startswith("arn:aws:acm:") == True


def test_add_records(route53_session):
    response =  route53_session.create_hosted_zone(Name='1234', CallerReference='1234')

    route53_session.change_resource_record_sets(
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
    
    assert add_records(route53_session, record , response['HostedZone']['Id'],"CREATE") == "INSYNC"



@patch("click.confirm")
def test_create_hosted_zone(mock_click, route53_session):
    route53_session.create_hosted_zone(Name='1234', CallerReference='1234')

    assert create_hosted_zone(route53_session, "test.test.1234", "test.1234", 1) == True


# Listcertificates is not implementaed in moto acm. Neeed to patch it
@patch(
        "commands.dns_cli.create_cert",
        return_value="arn:1234",
)
def test_check_r53(create_cert, route53_session):
    session = boto3.session.Session(profile_name="foo")
    route53_session.create_hosted_zone(Name='test.1234', CallerReference='1234')

    assert check_r53(session, session, "test.test.1234", "test.1234") == "arn:1234"



@patch(
        "commands.dns_cli.check_aws_conn",
)
@patch(
    "commands.dns_cli.check_r53",
    return_value="arn:1234",
)
def test_check_domain(check_aws_conn, check_r53, fakefs):
    fakefs.create_file(
            "manifest.yml",
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
    result = runner.invoke(check_domain, ["--path", "/", "--domain-profile", "foo", "--project-profile", "foo", "--base-domain", "test.1234"])
    assert result.output.startswith("Checking file: /manifest.yml\nDomains listed in manifest file") == True


@patch(
        "commands.dns_cli.check_aws_conn",
)
@patch(
        "commands.dns_cli.check_response",
        return_value="{}"
        #return_value="{'clusterArns': ['arn:aws:ecs:eu-west-2:12345:cluster/test',],}"
)
#@mock_sts
def test_assign_domain(check_aws_conn, check_response):
    #iam_session.create_account_alias(AccountAlias="foo")

    runner = CliRunner()
    result = runner.invoke(assign_domain, ["--app", "some-app", "--domain-profile", "foo", "--project-profile", "foo", "--svc", "web", "--env", "dev"])
    assert result.output.startswith("There are no clusters matching") == True
