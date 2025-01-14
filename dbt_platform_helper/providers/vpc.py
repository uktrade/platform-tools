from dataclasses import dataclass

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.aws import AWSException


class VpcProviderException(PlatformException):
    pass


class SubnetsNotFoundException(VpcProviderException):
    pass


@dataclass
class Vpc:
    public_subnets: list[str]
    private_subnets: list[str]
    security_groups: list[str]


class VpcProvider:
    def __init__(self, session):
        self.ec2_client = session.client("ec2")
        self.ec2_resource = session.resource("ec2")

    def get_subnet_ids(self, vpc_id):
        subnets = self.ec2_client.describe_subnets(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )["Subnets"]

        if not subnets:
            raise SubnetsNotFoundException(f"No subnets found for VPC with id: {vpc_id}.", fg="red")

        public_tag = {"Key": "subnet_type", "Value": "public"}
        public_subnets = [subnet["SubnetId"] for subnet in subnets if public_tag in subnet["Tags"]]
        private_tag = {"Key": "subnet_type", "Value": "private"}
        private_subnets = [
            subnet["SubnetId"] for subnet in subnets if private_tag in subnet["Tags"]
        ]

        return public_subnets, private_subnets

    def get_vpc_id_by_name(self, vpc_name: str) -> str:
        vpc_response = self.ec2_client.describe_vpcs(
            Filters=[{"Name": "tag:Name", "Values": [vpc_name]}]
        )

        matching_vpcs = vpc_response.get("Vpcs", [])

        if not matching_vpcs:
            raise AWSException(f"VPC not found for name '{vpc_name}'")

        vpc_id = vpc_response["Vpcs"][0].get("VpcId")

        # bit of a random check - i'd vote to remove this since the every vpc needs a one...
        if not vpc_id:
            raise AWSException(f"VPC id not present in vpc '{vpc_name}'")

        return vpc_id

    def get_vpc_info_by_name(self, app: str, env: str, vpc_name: str) -> Vpc:

        vpc_id = self.get_vpc_id_by_name(vpc_name)

        vpc = self.ec2_resource.Vpc(vpc_id)

        route_tables = self.ec2_client.describe_route_tables(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )["RouteTables"]

        private_subnets = []
        for route_table in route_tables:
            private_routes = [route for route in route_table["Routes"] if "NatGatewayId" in route]
            if not private_routes:
                continue
            for association in route_table["Associations"]:
                if "SubnetId" in association:
                    subnet_id = association["SubnetId"]
                    private_subnets.append(subnet_id)

        if not private_subnets:
            raise AWSException(f"No private subnets found in vpc '{vpc_name}'")

        tag_value = {"Key": "Name", "Value": f"copilot-{app}-{env}-env"}
        sec_groups = [sg.id for sg in vpc.security_groups.all() if sg.tags and tag_value in sg.tags]

        if not sec_groups:
            raise AWSException(f"No matching security groups found in vpc '{vpc_name}'")

        return Vpc([], private_subnets, sec_groups)
