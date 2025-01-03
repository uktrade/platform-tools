import pytest
from moto import mock_aws

from dbt_platform_helper.providers.aws import AWSException
from dbt_platform_helper.providers.vpc import Vpc
from dbt_platform_helper.providers.vpc import VpcProvider
from tests.platform_helper.utils.test_aws import ObjectWithId
from tests.platform_helper.utils.test_aws import mock_vpc_info_session


@mock_aws
def test_get_vpc_info_by_name_success():
    mock_session, mock_client, _ = mock_vpc_info_session()
    vpc_provider = VpcProvider(mock_session)

    result = vpc_provider.get_vpc_info_by_name("my_app", "my_env", "my_vpc")

    expected_vpc = Vpc(
        subnets=["subnet-private-1", "subnet-private-2"], security_groups=["sg-abc123"]
    )

    mock_client.describe_vpcs.assert_called_once_with(
        Filters=[{"Name": "tag:Name", "Values": ["my_vpc"]}]
    )

    assert result.subnets == expected_vpc.subnets
    assert result.security_groups == expected_vpc.security_groups


@mock_aws
def test_get_vpc_info_by_name_failure_no_matching_vpc():
    mock_session, mock_client, _ = mock_vpc_info_session()
    vpc_provider = VpcProvider(mock_session)

    vpc_data = {"Vpcs": []}
    mock_client.describe_vpcs.return_value = vpc_data

    with pytest.raises(AWSException) as ex:
        vpc_provider.get_vpc_info_by_name("my_app", "my_env", "my_vpc")

    assert "VPC not found for name 'my_vpc'" in str(ex)


@mock_aws
def test_get_vpc_info_by_name_failure_no_vpc_id_in_response():
    mock_session, mock_client, _ = mock_vpc_info_session()
    vpc_provider = VpcProvider(mock_session)

    vpc_data = {"Vpcs": [{"Id": "abc123"}]}
    mock_client.describe_vpcs.return_value = vpc_data

    with pytest.raises(AWSException) as ex:
        vpc_provider.get_vpc_info_by_name("my_app", "my_env", "my_vpc")

    assert "VPC id not present in vpc 'my_vpc'" in str(ex)


@mock_aws
def test_get_vpc_info_by_name_failure_no_private_subnets_in_vpc():
    mock_session, mock_client, _ = mock_vpc_info_session()
    vpc_provider = VpcProvider(mock_session)

    mock_client.describe_route_tables.return_value = {
        "RouteTables": [
            {
                "Associations": [
                    {
                        "Main": True,
                        "RouteTableId": "rtb-00cbf3c8d611a46b8",
                    }
                ],
                "Routes": [
                    {
                        "DestinationCidrBlock": "10.151.0.0/16",
                        "GatewayId": "local",
                        "Origin": "CreateRouteTable",
                        "State": "active",
                    }
                ],
                "VpcId": "vpc-010327b71b948b4bc",
                "OwnerId": "891377058512",
            }
        ]
    }

    with pytest.raises(AWSException) as ex:
        vpc_provider.get_vpc_info_by_name("my_app", "my_env", "my_vpc")

    assert "No private subnets found in vpc 'my_vpc'" in str(ex)


@mock_aws
def test_get_vpc_info_by_name_failure_no_matching_security_groups():
    mock_session, _, mock_vpc = mock_vpc_info_session()
    vpc_provider = VpcProvider(mock_session)

    mock_vpc.security_groups.all.return_value = [
        ObjectWithId("sg-abc345", tags=[]),
        ObjectWithId("sg-abc567", tags=[{"Key": "Name", "Value": "copilot-other_app-my_env-env"}]),
        ObjectWithId("sg-abc456"),
        ObjectWithId("sg-abc678", tags=[{"Key": "Name", "Value": "copilot-my_app-other_env-env"}]),
    ]

    with pytest.raises(AWSException) as ex:
        vpc_provider.get_vpc_info_by_name("my_app", "my_env", "my_vpc")

    assert "No matching security groups found in vpc 'my_vpc'" in str(ex)
