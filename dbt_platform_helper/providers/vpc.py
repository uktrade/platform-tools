from dataclasses import dataclass

from dbt_platform_helper.platform_exception import PlatformException


class VpcProviderException(PlatformException):
    pass


class SubnetsNotFoundException(VpcProviderException):
    pass


class PrivateSubnetsNotFoundException(VpcProviderException):
    pass


class PublicSubnetsNotFoundException(VpcProviderException):
    pass


class SecurityGroupNotFoundException(VpcProviderException):
    pass


class VpcNotFoundForNameException(VpcProviderException):
    pass


class VpcIdMissingException(VpcProviderException):
    pass


@dataclass
class Vpc:
    id: str
    public_subnets: list[str]
    private_subnets: list[str]
    security_groups: list[str]


class VpcProvider:
    def __init__(self, session):
        self.ec2_client = session.client("ec2")

    def _get_subnet_ids(self, vpc_id):
        subnets = self.ec2_client.describe_subnets(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        ).get("Subnets")

        if not subnets:
            raise SubnetsNotFoundException(f"No subnets found for VPC with id: {vpc_id}.")

        public_tag = {"Key": "subnet_type", "Value": "public"}
        public_subnets = [subnet["SubnetId"] for subnet in subnets if public_tag in subnet["Tags"]]

        private_tag = {"Key": "subnet_type", "Value": "private"}
        private_subnets = [
            subnet["SubnetId"] for subnet in subnets if private_tag in subnet["Tags"]
        ]

        return public_subnets, private_subnets

    def _get_vpc_id_by_name(self, vpc_name: str) -> str:
        vpcs = self.ec2_client.describe_vpcs(
            Filters=[{"Name": "tag:Name", "Values": [vpc_name]}]
        ).get("Vpcs", [])

        if not vpcs:
            raise VpcNotFoundForNameException(f"VPC not found for name '{vpc_name}'")

        vpc_id = vpcs[0].get("VpcId")

        if not vpc_id:
            raise VpcIdMissingException(f"VPC id not present in vpc '{vpc_name}'")

        return vpc_id

    def _get_security_groups(self, app: str, env: str, vpc_id: str) -> list:
        vpc_filter = {"Name": "vpc-id", "Values": [vpc_id]}
        # TODO Handle terraformed environment SG https://uktrade.atlassian.net/browse/DBTP-2074
        tag_filter = {"Name": f"tag:Name", "Values": [f"copilot-{app}-{env}-env"]}
        response = self.ec2_client.describe_security_groups(Filters=[vpc_filter, tag_filter])

        return [sg.get("GroupId") for sg in response.get("SecurityGroups")]

    def get_vpc(self, app: str, env: str, vpc_name: str) -> Vpc:

        vpc_id = self._get_vpc_id_by_name(vpc_name)

        public_subnets, private_subnets = self._get_subnet_ids(vpc_id)

        if not private_subnets:
            raise PrivateSubnetsNotFoundException(f"No private subnets found in vpc '{vpc_name}'")

        if not public_subnets:
            raise PublicSubnetsNotFoundException(f"No public subnets found in vpc '{vpc_name}'")

        sec_groups = self._get_security_groups(app, env, vpc_id)

        return Vpc(vpc_id, public_subnets, private_subnets, sec_groups)
