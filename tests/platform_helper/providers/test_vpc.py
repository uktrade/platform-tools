from unittest.mock import Mock

import boto3
import pytest
from moto import mock_aws

from dbt_platform_helper.providers.vpc import Vpc
from dbt_platform_helper.providers.vpc import VpcProvider
from dbt_platform_helper.providers.vpc import VpcProviderException
from tests.platform_helper.utils.test_aws import mock_vpc_info_session


@mock_aws
def set_up_test_platform_vpc(
    client: boto3.client, cidr: str, private_subnet_cidr: str, public_subnet_cidr: str, name: str
):
    vpc_id = client.create_vpc(CidrBlock=cidr)["Vpc"]["VpcId"]
    public_subnet_id = client.create_subnet(CidrBlock=public_subnet_cidr, VpcId=vpc_id)["Subnet"][
        "SubnetId"
    ]
    private_subnet_id = client.create_subnet(CidrBlock=private_subnet_cidr, VpcId=vpc_id)["Subnet"][
        "SubnetId"
    ]
    sg_id = client.create_security_group(
        GroupName="test_vpc_sg",
        Description=f"SG for {name}",
        VpcId=vpc_id,
    )["GroupId"]

    client.create_tags(Resources=[vpc_id], Tags=[{"Key": "Name", "Value": name}])
    client.create_tags(
        Resources=[public_subnet_id],
        Tags=[{"Key": "vpc-id", "Value": name}, {"Key": "subnet_type", "Value": "public"}],
    )
    client.create_tags(
        Resources=[private_subnet_id],
        Tags=[{"Key": "vpc-id", "Value": name}, {"Key": "subnet_type", "Value": "private"}],
    )
    client.create_tags(
        Resources=[sg_id], Tags=[{"Key": "Name", "Value": "copilot-test-app-test-env-env"}]
    )

    return Vpc(
        vpc_id,
        [public_subnet_id],
        [private_subnet_id],
        [sg_id],
    )


class TestGetVpcBotoIntegration:
    @mock_aws
    def test_get_vpc_success(self):
        client = boto3.client("ec2")
        expected_vpc = set_up_test_platform_vpc(
            client,
            "10.0.0.0/16",
            private_subnet_cidr="10.0.2.0/24",
            public_subnet_cidr="10.0.1.0/24",
            name="test-vpc",
        )
        set_up_test_platform_vpc(
            client,
            "172.16.0.0/16",
            private_subnet_cidr="172.16.2.0/24",
            public_subnet_cidr="172.16.1.0/24",
            name="test-vpc-2",
        )

        mock_session = Mock()
        mock_session.client.return_value = client

        result = VpcProvider(mock_session).get_vpc("test-app", "test-env", "test-vpc")

        assert result == expected_vpc

    @mock_aws
    def test_get_vpc_failure_no_matching_vpc(self):
        client = boto3.client("ec2")
        set_up_test_platform_vpc(
            client,
            "10.0.0.0/16",
            private_subnet_cidr="10.0.2.0/24",
            public_subnet_cidr="10.0.1.0/24",
            name="test-vpc",
        )

        mock_session = Mock()
        mock_session.client.return_value = client

        with pytest.raises(VpcProviderException) as ex:
            VpcProvider(mock_session).get_vpc("my_app", "my_env", "non-existent-vpc")

        assert "VPC not found for name 'non-existent-vpc'" in str(ex)

    @mock_aws
    def test_get_vpc_failure_no_vpcs(self):
        mock_session = Mock()
        mock_session.client.return_value = boto3.client("ec2")

        with pytest.raises(VpcProviderException) as ex:
            VpcProvider(mock_session).get_vpc("my_app", "my_env", "test-vpc")

        assert "VPC not found for name 'test-vpc'" in str(ex)


class TestGetVpcGivenMockedResponses:
    @mock_aws
    def test_get_vpc_sucess_given_mocked_responses(self):
        mock_session, mock_client, _ = mock_vpc_info_session()

        vpc_provider = VpcProvider(mock_session)

        result = vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

        mock_client.describe_vpcs.assert_called_once_with(
            Filters=[{"Name": "tag:Name", "Values": ["my_vpc"]}]
        )

        mock_client.describe_subnets.assert_called_once_with(
            Filters=[{"Name": "vpc-id", "Values": ["vpc-123456"]}]
        )

        mock_client.describe_security_groups.assert_called_once_with(
            Filters=[
                {"Name": "vpc-id", "Values": ["vpc-123456"]},
                {"Name": "tag:Name", "Values": ["copilot-my_app-my_env-env"]},
            ]
        )

        expected_vpc = Vpc(
            id="vpc-123456",
            public_subnets=["subnet-public-1", "subnet-public-2"],
            private_subnets=["subnet-private-1", "subnet-private-2"],
            security_groups=["sg-abc123"],
        )

        assert result == expected_vpc

    @mock_aws
    def test_get_vpc_failure_given_no_vpcs_response(self):
        mock_session, mock_client, _ = mock_vpc_info_session()
        vpc_provider = VpcProvider(mock_session)

        no_vpcs_response = {"Vpcs": []}
        mock_client.describe_vpcs.return_value = no_vpcs_response

        with pytest.raises(VpcProviderException) as ex:
            vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

        assert "VPC not found for name 'my_vpc'" in str(ex)

    @mock_aws
    def test_get_vpc_failure_no_vpc_id_in_response(self):
        mock_session, mock_client, _ = mock_vpc_info_session()
        vpc_provider = VpcProvider(mock_session)

        vpc_data = {"Vpcs": [{"Id": "abc123"}]}
        mock_client.describe_vpcs.return_value = vpc_data

        with pytest.raises(VpcProviderException) as ex:
            vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

        assert "VPC id not present in vpc 'my_vpc'" in str(ex)

    @mock_aws
    def test_get_vpc_failure_no_matching_private_subnets_in_response(self):
        mock_session, mock_client, _ = mock_vpc_info_session()
        mock_client.describe_subnets.return_value = {
            "Subnets": [
                {
                    "SubnetId": "test",
                    "Tags": [
                        {"Key": "subnet_type", "Value": "public"},
                    ],
                    "VpcId": "vpc-123456",
                }
            ]
        }
        vpc_provider = VpcProvider(mock_session)

        with pytest.raises(VpcProviderException) as ex:
            vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

        assert "No private subnets found in vpc 'my_vpc'" in str(ex)

    @mock_aws
    def test_get_vpc_failure_no_matching_public_subnets_in_response(self):
        mock_session, mock_client, _ = mock_vpc_info_session()
        mock_client.describe_subnets.return_value = {
            "Subnets": [
                {
                    "SubnetId": "test",
                    "Tags": [
                        {"Key": "subnet_type", "Value": "private"},
                    ],
                    "VpcId": "vpc-123456",
                }
            ]
        }
        vpc_provider = VpcProvider(mock_session)

        with pytest.raises(VpcProviderException) as ex:
            vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

        assert "No public subnets found in vpc 'my_vpc'" in str(ex)

    @mock_aws
    def test_get_vpc_failure_no_matching_security_groups_in_response(self):
        mock_session, mock_client, _ = mock_vpc_info_session()
        vpc_provider = VpcProvider(mock_session)

        mock_client.describe_security_groups.return_value = {"SecurityGroups": []}

        with pytest.raises(VpcProviderException) as ex:
            vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

        assert "No matching security groups found in vpc 'my_vpc'" in str(ex)
