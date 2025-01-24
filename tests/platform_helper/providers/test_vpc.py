from unittest.mock import Mock

import boto3
import pytest
from moto import mock_aws

from dbt_platform_helper.providers.vpc import Vpc
from dbt_platform_helper.providers.vpc import VpcProvider
from dbt_platform_helper.providers.vpc import VpcProviderException
from tests.platform_helper.utils.test_aws import mock_vpc_info_session


def set_up_test_platform_vpc(
    client: boto3.client, cidr: str, private_subnet_cidr: str, public_subnet_cidr: str, name: str
):
    vpc = client.create_vpc(CidrBlock=cidr)
    client.create_tags(Resources=[vpc["Vpc"]["VpcId"]], Tags=[{"Key": "Name", "Value": name}])
    public_subnet = client.create_subnet(CidrBlock=public_subnet_cidr, VpcId=vpc["Vpc"]["VpcId"])
    private_subnet = client.create_subnet(CidrBlock=private_subnet_cidr, VpcId=vpc["Vpc"]["VpcId"])

    client.create_tags(
        Resources=[public_subnet["Subnet"]["SubnetId"]],
        Tags=[{"Key": "vpc-id", "Value": name}, {"Key": "subnet_type", "Value": "public"}],
    )
    client.create_tags(
        Resources=[private_subnet["Subnet"]["SubnetId"]],
        Tags=[{"Key": "vpc-id", "Value": name}, {"Key": "subnet_type", "Value": "private"}],
    )

    sg_tag = "copilot-test-app-test-env-env"
    sg = client.create_security_group(
        GroupName="test_vpc_sg",
        Description="SG tagged with expected name",
        VpcId=vpc["Vpc"]["VpcId"],
    )
    client.create_tags(Resources=[sg["GroupId"]], Tags=[{"Key": "Name", "Value": sg_tag}])

    return Vpc(
        vpc["Vpc"]["VpcId"],
        [public_subnet["Subnet"]["SubnetId"]],
        [private_subnet["Subnet"]["SubnetId"]],
        [sg["GroupId"]],
    )


@mock_aws
def test_get_vpc_success_against_mocked_aws_environment():
    client = boto3.client("ec2")
    expected_vpc = set_up_test_platform_vpc(
        client,
        "10.0.0.0/16",
        private_subnet_cidr="10.0.2.0/24",
        public_subnet_cidr="10.0.1.0/24",
        name="test-vpc",
    )
    non_matching_vpc = set_up_test_platform_vpc(
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
def test_get_vpc_success():
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

    assert result.public_subnets == expected_vpc.public_subnets
    assert result.private_subnets == expected_vpc.private_subnets
    assert result.security_groups == expected_vpc.security_groups
    assert result.id == expected_vpc.id


@mock_aws
def test_get_vpc_failure_no_matching_vpc():
    mock_session, mock_client, _ = mock_vpc_info_session()
    vpc_provider = VpcProvider(mock_session)

    no_vpcs_response = {"Vpcs": []}
    mock_client.describe_vpcs.return_value = no_vpcs_response

    with pytest.raises(VpcProviderException) as ex:
        vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

    assert "VPC not found for name 'my_vpc'" in str(ex)


@mock_aws
def test_get_vpc_failure_no_vpc_id_in_response():
    mock_session, mock_client, _ = mock_vpc_info_session()
    vpc_provider = VpcProvider(mock_session)

    vpc_data = {"Vpcs": [{"Id": "abc123"}]}
    mock_client.describe_vpcs.return_value = vpc_data

    with pytest.raises(VpcProviderException) as ex:
        vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

    assert "VPC id not present in vpc 'my_vpc'" in str(ex)


@mock_aws
def test_get_vpc_failure_no_private_subnets_in_vpc():
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
def test_get_vpc_failure_no_public_subnets_in_vpc():
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
def test_get_vpc_failure_no_matching_security_groups():
    mock_session, mock_client, _ = mock_vpc_info_session()
    vpc_provider = VpcProvider(mock_session)

    mock_client.describe_security_groups.return_value = {"SecurityGroups": []}

    with pytest.raises(VpcProviderException) as ex:
        vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

    assert "No matching security groups found in vpc 'my_vpc'" in str(ex)
