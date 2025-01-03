from boto3 import Session

from dbt_platform_helper.providers.aws import AWSException


class Vpc:
    def __init__(self, subnets: list[str], security_groups: list[str]):
        self.subnets = subnets
        self.security_groups = security_groups


def get_vpc_info_by_name(session: Session, app: str, env: str, vpc_name: str) -> Vpc:
    ec2_client = session.client("ec2")
    vpc_response = ec2_client.describe_vpcs(Filters=[{"Name": "tag:Name", "Values": [vpc_name]}])

    matching_vpcs = vpc_response.get("Vpcs", [])

    if not matching_vpcs:
        raise AWSException(f"VPC not found for name '{vpc_name}'")

    vpc_id = vpc_response["Vpcs"][0].get("VpcId")

    if not vpc_id:
        raise AWSException(f"VPC id not present in vpc '{vpc_name}'")

    ec2_resource = session.resource("ec2")
    vpc = ec2_resource.Vpc(vpc_id)

    route_tables = ec2_client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["RouteTables"]

    subnets = []
    for route_table in route_tables:
        private_routes = [route for route in route_table["Routes"] if "NatGatewayId" in route]
        if not private_routes:
            continue
        for association in route_table["Associations"]:
            if "SubnetId" in association:
                subnet_id = association["SubnetId"]
                subnets.append(subnet_id)

    if not subnets:
        raise AWSException(f"No private subnets found in vpc '{vpc_name}'")

    tag_value = {"Key": "Name", "Value": f"copilot-{app}-{env}-env"}
    sec_groups = [sg.id for sg in vpc.security_groups.all() if sg.tags and tag_value in sg.tags]

    if not sec_groups:
        raise AWSException(f"No matching security groups found in vpc '{vpc_name}'")

    return Vpc(subnets, sec_groups)
