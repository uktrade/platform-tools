import re
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import boto3
import click
import pytest
import yaml
from moto import mock_aws

from dbt_platform_helper.domain.copilot_environment import CertificateNotFoundException
from dbt_platform_helper.domain.copilot_environment import CopilotEnvironment
from dbt_platform_helper.domain.copilot_environment import CopilotTemplating
from dbt_platform_helper.domain.copilot_environment import find_https_certificate
from dbt_platform_helper.domain.copilot_environment import get_cert_arn
from dbt_platform_helper.providers.vpc import Vpc

# @mock_aws
# def test_get_subnet_ids_with_cloudformation_export_returning_a_different_order():
#     # This test and the associated behavior can be removed when we stop using AWS Copilot to deploy the services
#     def _list_exports_subnet_object(environment: str, subnet_ids: list[str], visibility: str):
#         return {
#             "Name": f"application-{environment}-{visibility.capitalize()}Subnets",
#             "Value": f"{','.join(subnet_ids)}",
#         }

#     def _describe_subnets_subnet_object(subnet_id: str, visibility: str):
#         return {
#             "SubnetId": subnet_id,
#             "Tags": [{"Key": "subnet_type", "Value": visibility}],
#         }

#     def _non_subnet_exports(number):
#         return [
#             {
#                 "Name": f"application-environment-NotASubnet",
#                 "Value": "does-not-matter",
#             }
#         ] * number

#     expected_public_subnet_id_1 = "subnet-1public"
#     expected_public_subnet_id_2 = "subnet-2public"
#     expected_private_subnet_id_1 = "subnet-1private"
#     expected_private_subnet_id_2 = "subnet-2private"

#     mock_boto3_session = MagicMock()

#     # Cloudformation list_exports returns a paginated response with the exports in the expected order plus some we are not interested in
#     mock_boto3_session.client("cloudformation").get_paginator(
#         "list_exports"
#     ).paginate.return_value = [
#         {"Exports": _non_subnet_exports(5)},
#         {
#             "Exports": [
#                 _list_exports_subnet_object(
#                     "environment",
#                     [
#                         expected_public_subnet_id_1,
#                         expected_public_subnet_id_2,
#                     ],
#                     "public",
#                 ),
#                 _list_exports_subnet_object(
#                     "environment",
#                     [
#                         expected_private_subnet_id_1,
#                         expected_private_subnet_id_2,
#                     ],
#                     "private",
#                 ),
#                 _list_exports_subnet_object(
#                     "otherenvironment",
#                     [expected_public_subnet_id_1],
#                     "public",
#                 ),
#                 _list_exports_subnet_object(
#                     "otherenvironment",
#                     [expected_private_subnet_id_2],
#                     "private",
#                 ),
#             ]
#         },
#         {"Exports": _non_subnet_exports(5)},
#     ]

#     # EC2 client should return them in an order that differs from the CloudFormation Export
#     mock_boto3_session.client("ec2").describe_subnets.return_value = {
#         "Subnets": [
#             _describe_subnets_subnet_object(expected_public_subnet_id_2, "public"),
#             _describe_subnets_subnet_object(expected_public_subnet_id_1, "public"),
#             _describe_subnets_subnet_object(expected_private_subnet_id_2, "private"),
#             _describe_subnets_subnet_object(expected_private_subnet_id_1, "private"),
#         ]
#     }

#     # Act (there's a lot of setup, worth signposting where this happens)
#     public_subnet_ids, private_subnet_ids = get_subnet_ids(
#         mock_boto3_session, "vpc-id-does-not-matter", "environment"
#     )

#     assert public_subnet_ids == [
#         expected_public_subnet_id_1,
#         expected_public_subnet_id_2,
#     ]
#     assert private_subnet_ids == [
#         expected_private_subnet_id_1,
#         expected_private_subnet_id_2,
#     ]


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


class TestCrossEnvironmentS3Templating:
    def environments(self):
        return {
            "dev": {"accounts": {"deploy": {"name": "dev-acc", "id": "123456789010"}}},
            "staging": {"accounts": {"deploy": {"name": "dev-acc", "id": "123456789010"}}},
            "hotfix": {"accounts": {"deploy": {"name": "prod-acc", "id": "987654321010"}}},
            "prod": {"accounts": {"deploy": {"name": "prod-acc", "id": "987654321010"}}},
        }

    def s3_xenv_extensions(self):
        return {
            "test-s3-bucket-x-account": {
                "type": "s3",
                "services": "test-svc",
                "environments": {
                    "hotfix": {
                        "bucket_name": "x-acc-bucket",
                        "cross_environment_service_access": {
                            "test_access": {
                                "application": "app2",
                                "environment": "staging",
                                "account": "123456789010",
                                "service": "test_svc",
                                "read": True,
                                "write": True,
                                "cyber_sign_off_by": "user@example.com",
                            }
                        },
                    }
                },
            }
        }

    def s3_xenv_multiple_extensions(self):
        return {
            "test-s3-1": {
                "type": "s3",
                "services": "test-svc",
                "environments": {
                    "hotfix": {
                        "bucket_name": "x-acc-bucket-1",
                        "cross_environment_service_access": {
                            "test_access_1": {
                                "application": "app1",
                                "environment": "staging",
                                "account": "123456789010",
                                "service": "other_svc_1",
                                "read": True,
                                "write": True,
                                "cyber_sign_off_by": "user1@example.com",
                            },
                            "test_access_2": {
                                "application": "app2",
                                "environment": "dev",
                                "account": "123456789010",
                                "service": "other_svc_2",
                                "read": True,
                                "write": False,
                                "cyber_sign_off_by": "user2@example.com",
                            },
                        },
                    },
                },
            },
            "test-s3-2": {
                "type": "s3",
                "services": "test-svc",
                "environments": {
                    "dev": {
                        "bucket_name": "x-acc-bucket-2",
                        "cross_environment_service_access": {
                            "test_access_3": {
                                "application": "app2",
                                "environment": "hotfix",
                                "account": "987654321010",
                                "service": "other_svc_2",
                                "read": False,
                                "write": True,
                                "cyber_sign_off_by": "user@example.com",
                            }
                        },
                    },
                    "prod": {
                        "bucket_name": "x-acc-bucket-3",
                        "cross_environment_service_access": {
                            "test_access_4": {
                                "application": "app2",
                                "environment": "staging",
                                "account": "123456789010",
                                "service": "other_svc_3",
                                "read": True,
                                "write": True,
                                "cyber_sign_off_by": "user@example.com",
                            }
                        },
                    },
                    "hotfix": {
                        "bucket_name": "x-acc-bucket-4",
                        "cross_environment_service_access": {
                            "test_access_5": {
                                "application": "app2",
                                "environment": "staging",
                                "account": "123456789010",
                                "service": "other_svc_4",
                                "read": False,
                                "write": False,
                                "cyber_sign_off_by": "user@example.com",
                            }
                        },
                    },
                },
            },
        }

    def test_generate_cross_account_s3_policies(self):
        """
        Tests the happy path test for the simple case.

        Also tests passed in templates
        """
        mock_mkfile = Mock()
        provider = CopilotTemplating(mkfile_fn=mock_mkfile)
        provider.generate_cross_account_s3_policies(self.environments(), self.s3_xenv_extensions())

        assert mock_mkfile.call_count == 1

        calls = mock_mkfile.call_args_list

        act_output_dir = calls[0][0][0]
        act_output_path = calls[0][0][1]
        act_content = calls[0][0][2]
        act_overwrite_file = calls[0][0][3]

        self.assert_headers_present(act_content)

        assert act_output_dir == Path(".").absolute()
        assert act_output_path == "copilot/test_svc/addons/s3-cross-account-policy.yml"
        assert act_overwrite_file

        act = yaml.safe_load(act_content)

        assert act["Parameters"]["App"]["Type"] == "String"
        assert act["Parameters"]["Env"]["Type"] == "String"
        assert act["Parameters"]["Name"]["Type"] == "String"

        assert (
            act["Outputs"]["testSvcXAccBucketTestAccessXEnvAccessPolicy"]["Description"]
            == "The IAM::ManagedPolicy to attach to the task role"
        )
        assert (
            act["Outputs"]["testSvcXAccBucketTestAccessXEnvAccessPolicy"]["Value"]["Ref"]
            == "testSvcXAccBucketTestAccessXEnvAccessPolicy"
        )

        policy = act["Resources"]["testSvcXAccBucketTestAccessXEnvAccessPolicy"]
        assert (
            policy["Metadata"]["aws:copilot:description"]
            == "An IAM ManagedPolicy for your service to access the bucket"
        )
        assert policy["Type"] == "AWS::IAM::ManagedPolicy"

        policy_doc = policy["Properties"]["PolicyDocument"]
        assert policy_doc["Version"] == date(2012, 10, 17)
        statements = policy_doc["Statement"]
        kms_statement = statements[0]
        assert kms_statement["Sid"] == "KMSDecryptAndGenerate"
        assert kms_statement["Effect"] == "Allow"
        assert kms_statement["Action"] == ["kms:Decrypt", "kms:GenerateDataKey"]
        assert kms_statement["Resource"] == "arn:aws:kms:eu-west-2:987654321010:key/*"
        assert kms_statement["Condition"] == {
            "StringEquals": {"aws:PrincipalTag/copilot-environment": ["staging"]}
        }

        s3_obj_statement = statements[1]
        assert s3_obj_statement["Sid"] == "S3ObjectActions"
        assert s3_obj_statement["Effect"] == "Allow"
        assert s3_obj_statement["Action"] == ["s3:Get*", "s3:Put*"]
        assert s3_obj_statement["Resource"] == "arn:aws:s3:::x-acc-bucket/*"
        assert s3_obj_statement["Condition"] == {
            "StringEquals": {"aws:PrincipalTag/copilot-environment": ["staging"]}
        }

        s3_list_statement = statements[2]
        assert s3_list_statement["Sid"] == "S3ListAction"
        assert s3_list_statement["Effect"] == "Allow"
        assert s3_list_statement["Action"] == ["s3:ListBucket"]
        assert s3_list_statement["Resource"] == "arn:aws:s3:::x-acc-bucket"
        assert s3_list_statement["Condition"] == {
            "StringEquals": {"aws:PrincipalTag/copilot-environment": ["staging"]}
        }

    @staticmethod
    def assert_headers_present(act_content):
        content_lines = [line.strip() for line in act_content.split("\n", 3)]
        assert (
            content_lines[0] == "# WARNING: This is an autogenerated file, not for manual editing."
        )
        assert re.match(
            r"# Generated by platform-helper \d+\.\d+\.\d+ / \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
            content_lines[1],
        )

    def test_generate_cross_account_s3_policies_no_addons(self):
        mock_mkfile = Mock()
        provider = CopilotTemplating(mkfile_fn=mock_mkfile)
        provider.generate_cross_account_s3_policies(self.environments(), {})

        assert mock_mkfile.call_count == 0

    def test_generate_cross_account_s3_policies_multiple_addons(self):
        """More comprehensive tests that check multiple corner cases."""
        mock_mkfile = Mock()
        provider = CopilotTemplating(mkfile_fn=mock_mkfile)
        provider.generate_cross_account_s3_policies(
            self.environments(), self.s3_xenv_multiple_extensions()
        )

        assert mock_mkfile.call_count == 3

        calls = mock_mkfile.call_args_list

        # Case 1: hotfix -> staging. other_svc_1
        act_output_dir = calls[0][0][0]
        act_output_path = calls[0][0][1]
        act_content = calls[0][0][2]
        act_overwrite_file = calls[0][0][3]
        act = yaml.safe_load(act_content)

        self.assert_headers_present(act_content)
        assert act_output_dir == Path(".").absolute()
        assert act_output_path == "copilot/other_svc_1/addons/s3-cross-account-policy.yml"
        assert act_overwrite_file

        assert act["Parameters"]["App"]["Type"] == "String"
        assert act["Parameters"]["Env"]["Type"] == "String"
        assert act["Parameters"]["Name"]["Type"] == "String"

        assert len(act["Outputs"]) == 1
        assert (
            act["Outputs"]["otherSvc1XAccBucket1TestAccess1XEnvAccessPolicy"]["Value"]["Ref"]
            == "otherSvc1XAccBucket1TestAccess1XEnvAccessPolicy"
        )
        assert len(act["Resources"]) == 1

        principal_tag = "aws:PrincipalTag/copilot-environment"

        policy_doc1 = act["Resources"]["otherSvc1XAccBucket1TestAccess1XEnvAccessPolicy"][
            "Properties"
        ]["PolicyDocument"]
        kms_statement1 = policy_doc1["Statement"][0]
        assert kms_statement1["Condition"]["StringEquals"][principal_tag] == ["staging"]
        assert kms_statement1["Resource"] == "arn:aws:kms:eu-west-2:987654321010:key/*"
        obj_act_statement1 = policy_doc1["Statement"][1]
        assert obj_act_statement1["Action"] == ["s3:Get*", "s3:Put*"]

        # Case 2: hotfix -> dev and dev -> hotfix. other_svc_2
        act_output_dir = calls[1][0][0]
        act_output_path = calls[1][0][1]
        act_content = calls[1][0][2]
        act_overwrite_file = calls[1][0][3]
        act = yaml.safe_load(act_content)

        self.assert_headers_present(act_content)
        assert act_output_dir == Path(".").absolute()
        assert act_output_path == "copilot/other_svc_2/addons/s3-cross-account-policy.yml"
        assert act_overwrite_file

        assert act["Parameters"]["App"]["Type"] == "String"
        assert act["Parameters"]["Env"]["Type"] == "String"
        assert act["Parameters"]["Name"]["Type"] == "String"

        assert len(act["Outputs"]) == 2
        assert (
            act["Outputs"]["otherSvc2XAccBucket1TestAccess2XEnvAccessPolicy"]["Value"]["Ref"]
            == "otherSvc2XAccBucket1TestAccess2XEnvAccessPolicy"
        )
        assert (
            act["Outputs"]["otherSvc2XAccBucket2TestAccess3XEnvAccessPolicy"]["Value"]["Ref"]
            == "otherSvc2XAccBucket2TestAccess3XEnvAccessPolicy"
        )

        policy_doc2 = act["Resources"]["otherSvc2XAccBucket1TestAccess2XEnvAccessPolicy"][
            "Properties"
        ]["PolicyDocument"]
        kms_statement2 = policy_doc2["Statement"][0]
        assert kms_statement2["Condition"]["StringEquals"][principal_tag] == ["dev"]
        assert kms_statement2["Resource"] == "arn:aws:kms:eu-west-2:987654321010:key/*"
        obj_act_statement2 = policy_doc2["Statement"][1]
        assert obj_act_statement2["Action"] == ["s3:Get*"]

        policy_doc3 = act["Resources"]["otherSvc2XAccBucket2TestAccess3XEnvAccessPolicy"][
            "Properties"
        ]["PolicyDocument"]
        kms_statement3 = policy_doc3["Statement"][0]
        assert kms_statement3["Condition"]["StringEquals"][principal_tag] == ["hotfix"]
        assert kms_statement3["Resource"] == "arn:aws:kms:eu-west-2:123456789010:key/*"
        obj_act_statement3 = policy_doc3["Statement"][1]
        assert obj_act_statement3["Action"] == ["s3:Put*"]

        # Case 3: prod -> staging. other_svc_3
        act_output_dir = calls[2][0][0]
        act_output_path = calls[2][0][1]
        act_content = calls[2][0][2]
        act_overwrite_file = calls[2][0][3]
        act = yaml.safe_load(act_content)

        self.assert_headers_present(act_content)
        assert act_output_dir == Path(".").absolute()
        assert act_output_path == "copilot/other_svc_3/addons/s3-cross-account-policy.yml"
        assert act_overwrite_file

        assert act["Parameters"]["App"]["Type"] == "String"
        assert act["Parameters"]["Env"]["Type"] == "String"
        assert act["Parameters"]["Name"]["Type"] == "String"

        assert len(act["Outputs"]) == 1

        assert (
            act["Outputs"]["otherSvc3XAccBucket3TestAccess4XEnvAccessPolicy"]["Value"]["Ref"]
            == "otherSvc3XAccBucket3TestAccess4XEnvAccessPolicy"
        )
        policy_doc4 = act["Resources"]["otherSvc3XAccBucket3TestAccess4XEnvAccessPolicy"][
            "Properties"
        ]["PolicyDocument"]
        kms_statement4 = policy_doc4["Statement"][0]
        assert kms_statement4["Condition"]["StringEquals"][principal_tag] == ["staging"]
        assert kms_statement4["Resource"] == "arn:aws:kms:eu-west-2:987654321010:key/*"
        obj_act_statement4 = policy_doc4["Statement"][1]
        assert obj_act_statement4["Action"] == ["s3:Get*", "s3:Put*"]


class TestCopilotTemplating:

    @patch(
        "dbt_platform_helper.domain.copilot_environment.get_cert_arn",
        return_value="arn:aws:acm:test",
    )
    @patch("dbt_platform_helper.domain.copilot_environment.get_aws_session_or_abort")
    def test_copilot_templating_generate_generates_expected_manifest(
        self, mock_get_cert_arn, mock_get_session
    ):

        mock_vpc_provider = Mock()
        mock_file_provider = Mock()

        mock_vpc_provider.get_vpc.return_value = Vpc(
            id="a-vpc-id",
            public_subnets=["a-public-subnet"],
            private_subnets=["a-private-subnet"],
            security_groups=["a-security-group"],
        )

        mocked_session = MagicMock()
        mock_get_session.return_value = mocked_session

        copilot_templating = CopilotTemplating(
            mock_vpc_provider, mock_file_provider, "im a file provider!"
        )

        result = copilot_templating.generate_copilot_environment_manifest(
            "connors-environment", "connors-application", {"config": "im config"}, mock_get_session
        )

        # TODO - assertions on the results...


class TestCopilotGenerate:

    @patch("dbt_platform_helper.domain.copilot_environment.get_aws_session_or_abort")
    def test_generate(self, mock_get_session):

        mock_copilot_templating = Mock()
        mock_config_provider = Mock()
        mock_vpc_provider = MagicMock()

        mocked_session = MagicMock()
        mock_get_session.return_value = mocked_session

        test_env_config = {
            "vpc": "vpc3",
            "accounts": {
                "deploy": {"name": "non-prod-acc", "id": "1122334455"},
                "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
            },
            "versions": {"terraform-platform-modules": "123456"},
        }
        config = {"application": "test-app", "environments": {"test_environment": test_env_config}}

        mock_config_provider.get_enriched_config.return_value = config

        copilot_environment = CopilotEnvironment(
            config_provider=mock_config_provider,
            vpc_provider=mock_vpc_provider,
            copilot_templating=mock_copilot_templating,
        )

        copilot_environment.generate(environment_name="test_environment")

        mock_copilot_templating.generate_copilot_environment_manifest.assert_called_once_with(
            environment_name="test_environment",
            application_name="test-app",
            env_config=test_env_config,
            session=mocked_session,
        )

    # def test_fail_early_if_platform_config_invalid(self, capfd):
    #     mock_file_provider = Mock()
    #     mock_file_provider.load.return_value = {}

    #     with patch(
    #         "dbt_platform_helper.providers.config.abort_with_error"
    #     ) as mock_abort_with_error:
    #         mock_abort_with_error.side_effect = SystemExit(1)
    #         with pytest.raises(SystemExit) as e:
    #             CopilotEnvironment(ConfigProvider(Mock(), mock_file_provider)).generate("test")

    #     assert e.value.code == 1

    #     mock_abort_with_error.assert_called_with(
    #         f"Schema error in platform-config.yml. Missing key: 'application'"
    #     )
    #     mock_file_provider.mkfile.assert_not_called()
