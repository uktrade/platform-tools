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
    client: boto3.client,
    app_name: str,
    env_name: str,
    cidr: str,
    private_subnet_cidr: str,
    public_subnet_cidr: str,
    name: str,
    copilot_security_group: bool = True,
    platform_security_group: bool = False,
):
    vpc_id = client.create_vpc(CidrBlock=cidr)["Vpc"]["VpcId"]
    public_subnet_id = client.create_subnet(CidrBlock=public_subnet_cidr, VpcId=vpc_id)["Subnet"][
        "SubnetId"
    ]
    private_subnet_id = client.create_subnet(CidrBlock=private_subnet_cidr, VpcId=vpc_id)["Subnet"][
        "SubnetId"
    ]
    client.create_tags(Resources=[vpc_id], Tags=[{"Key": "Name", "Value": name}])
    client.create_tags(
        Resources=[public_subnet_id],
        Tags=[{"Key": "vpc-id", "Value": name}, {"Key": "subnet_type", "Value": "public"}],
    )
    client.create_tags(
        Resources=[private_subnet_id],
        Tags=[{"Key": "vpc-id", "Value": name}, {"Key": "subnet_type", "Value": "private"}],
    )

    security_group_ids = []
    if copilot_security_group:
        copilot_sg_id = client.create_security_group(
            GroupName="test_copilot_vpc_sg",
            Description=f"Copilot SG for {name}",
            VpcId=vpc_id,
        )["GroupId"]

        client.create_tags(
            Resources=[copilot_sg_id],
            Tags=[{"Key": "Name", "Value": f"copilot-{app_name}-{env_name}-env"}],
        )
        security_group_ids.append(copilot_sg_id)

    if platform_security_group:
        platform_sg_id = client.create_security_group(
            GroupName="test_platform_vpc_sg",
            Description=f"Platform SG for {name}",
            VpcId=vpc_id,
        )["GroupId"]

        client.create_tags(
            Resources=[platform_sg_id],
            Tags=[{"Key": "Name", "Value": f"platform-{app_name}-{env_name}-env-sg"}],
        )
        security_group_ids.append(platform_sg_id)

    return Vpc(
        vpc_id,
        [public_subnet_id],
        [private_subnet_id],
        security_group_ids,
    )


class TestGetVpcBotoIntegration:
    @mock_aws
    @pytest.mark.parametrize(
        "copilot_sg, platform_sg, expected_sg_name",
        [
            (True, False, "test_copilot_vpc_sg"),
            (True, True, "test_platform_vpc_sg"),
            (False, True, "test_platform_vpc_sg"),
        ],
    )
    def test_get_vpc_successfully_selects_the_right_vpc(
        self, copilot_sg, platform_sg, expected_sg_name
    ):
        client = boto3.client("ec2")

        app = "test-app"
        env = "test-env"
        expected_vpc_1 = set_up_test_platform_vpc(
            client,
            app,
            env,
            "10.0.0.0/16",
            private_subnet_cidr="10.0.2.0/24",
            public_subnet_cidr="10.0.1.0/24",
            name="test-vpc",
            copilot_security_group=copilot_sg,
            platform_security_group=platform_sg,
        )
        expected_vpc_2 = set_up_test_platform_vpc(
            client,
            app,
            env,
            "172.16.0.0/16",
            private_subnet_cidr="172.16.2.0/24",
            public_subnet_cidr="172.16.1.0/24",
            name="test-vpc-2",
            copilot_security_group=copilot_sg,
            platform_security_group=platform_sg,
        )

        mock_session = Mock()
        mock_session.client.return_value = client

        result_1 = VpcProvider(mock_session).get_vpc(app, env, "test-vpc")
        assert result_1.public_subnets == expected_vpc_1.public_subnets
        assert result_1.private_subnets == expected_vpc_1.private_subnets
        assert len(result_1.security_groups) == 1

        vpc1_filter = {"Name": "vpc-id", "Values": [expected_vpc_1.id]}
        tag_filter = {"Name": "group-name", "Values": [expected_sg_name]}
        exp_security_group = client.describe_security_groups(Filters=[vpc1_filter, tag_filter]).get(
            "SecurityGroups"
        )[0]

        assert exp_security_group["SecurityGroupArn"].endswith(result_1.security_groups[0])

        result_2 = VpcProvider(mock_session).get_vpc(app, env, "test-vpc-2")
        assert result_2.public_subnets == expected_vpc_2.public_subnets
        assert result_2.private_subnets == expected_vpc_2.private_subnets
        assert len(result_2.security_groups) == 1

        vpc2_filter = {"Name": "vpc-id", "Values": [expected_vpc_2.id]}
        exp_security_group_2 = client.describe_security_groups(
            Filters=[vpc2_filter, tag_filter]
        ).get("SecurityGroups")[0]

        assert exp_security_group_2["SecurityGroupArn"].endswith(result_2.security_groups[0])

    @mock_aws
    def test_get_vpc_failure_no_matching_vpc_name(self):
        client = boto3.client("ec2")
        set_up_test_platform_vpc(
            client,
            "my_app",
            "my_env",
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

    @mock_aws
    def test_get_vpc_success_given_no_security_groups_for_app(self):
        client = boto3.client("ec2")
        mock_vpc = set_up_test_platform_vpc(
            client,
            "my_app",
            "my_env",
            "10.0.0.0/16",
            private_subnet_cidr="10.0.2.0/24",
            public_subnet_cidr="10.0.1.0/24",
            name="test-vpc",
        )

        mock_vpc.security_groups = []

        mock_session = Mock()
        mock_session.client.return_value = client

        result = VpcProvider(mock_session).get_vpc(
            "no-security-groups-for-this-app", "my_env", "test-vpc"
        )
        assert result == mock_vpc

    @mock_aws
    def test_get_vpc_success_given_no_security_groups_for_the_environment(self):
        client = boto3.client("ec2")
        mock_vpc = set_up_test_platform_vpc(
            client,
            "my_app",
            "my_env",
            "10.0.0.0/16",
            private_subnet_cidr="10.0.2.0/24",
            public_subnet_cidr="10.0.1.0/24",
            name="test-vpc",
        )

        mock_vpc.security_groups = []

        mock_session = Mock()
        mock_session.client.return_value = client

        result = VpcProvider(mock_session).get_vpc(
            "my_app", "no_security_groups_in_this_env", "test-vpc"
        )

        assert result == mock_vpc


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
                {
                    "Name": "tag:Name",
                    "Values": ["copilot-my_app-my_env-env", "platform-my_app-my_env-env-sg"],
                },
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
    def test_get_vpc_success_no_matching_security_groups_in_response(self):
        mock_session, mock_client, _ = mock_vpc_info_session()
        vpc_provider = VpcProvider(mock_session)

        mock_client.describe_security_groups.return_value = {"SecurityGroups": []}

        expected_vpc = Vpc(
            id="vpc-123456",
            public_subnets=["subnet-public-1", "subnet-public-2"],
            private_subnets=["subnet-private-1", "subnet-private-2"],
            security_groups=[],
        )
        result = vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

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
    def test_get_vpc_failure_no_subnets_in_response(self):
        mock_session, mock_client, _ = mock_vpc_info_session()
        mock_client.describe_subnets.return_value = {"Subnets": []}
        vpc_provider = VpcProvider(mock_session)

        with pytest.raises(VpcProviderException) as ex:
            vpc_provider.get_vpc("my_app", "my_env", "my_vpc")

        assert "No subnets found for VPC with id: vpc-123456" in str(ex)
