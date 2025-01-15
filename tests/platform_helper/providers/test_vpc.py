import pytest
from moto import mock_aws

from dbt_platform_helper.providers.aws import AWSException
from dbt_platform_helper.providers.vpc import Vpc
from dbt_platform_helper.providers.vpc import VpcProvider
from tests.platform_helper.utils.test_aws import mock_vpc_info_session


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
            {"Name": "tag:Name", "Values": "copilot-my_app-my_env-env"},
        ]
    )

    expected_vpc = Vpc(
        public_subnets=["subnet-public-1", "subnet-public-2"],
        private_subnets=["subnet-private-1", "subnet-private-2"],
        security_groups=["sg-abc123"],
    )

    assert result.private_subnets == expected_vpc.private_subnets
    assert result.security_groups == expected_vpc.security_groups


@mock_aws
def test_get_vpc_failure_no_matching_vpc():
    mock_session, mock_client, _ = mock_vpc_info_session()
    vpc_provider = VpcProvider(mock_session)

    no_vpcs_response = {"Vpcs": []}
    mock_client.describe_vpcs.return_value = no_vpcs_response

    with pytest.raises(AWSException) as ex:
        vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

    assert "VPC not found for name 'my_vpc'" in str(ex)


@mock_aws
def test_get_vpc_failure_no_vpc_id_in_response():
    mock_session, mock_client, _ = mock_vpc_info_session()
    vpc_provider = VpcProvider(mock_session)

    vpc_data = {"Vpcs": [{"Id": "abc123"}]}
    mock_client.describe_vpcs.return_value = vpc_data

    with pytest.raises(AWSException) as ex:
        vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

    assert "VPC id not present in vpc 'my_vpc'" in str(ex)


@mock_aws
# TODO the necessity of a private subnet is specific to data copy
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

    with pytest.raises(AWSException) as ex:
        vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

    assert "No private subnets found in vpc 'my_vpc'" in str(ex)


@mock_aws
def test_get_vpc_failure_no_matching_security_groups():
    mock_session, mock_client, _ = mock_vpc_info_session()
    vpc_provider = VpcProvider(mock_session)

    mock_client.describe_security_groups.return_value = {"SecurityGroups": []}

    with pytest.raises(AWSException) as ex:
        vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

    assert "No matching security groups found in vpc 'my_vpc'" in str(ex)
