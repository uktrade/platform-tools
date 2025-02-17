import boto3
from boto3 import Session

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.aws import get_aws_session_or_abort


class LoadBalancerProvider:

    def __init__(self, session: Session = None, io: ClickIOProvider = ClickIOProvider()):
        self.session = session
        self.evlb_client = self._get_client("elbv2")

    def _get_client(self, client: str):
        if not self.session:
            self.session = get_aws_session_or_abort()
        return self.session.client(client)

    def get_https_certificate_for_application(self, app: str, env: str) -> str:
        return ""

    def get_https_listener_for_application(self, app: str, env: str) -> str:
        return ""

    def get_load_balancer_for_application(self, app: str, env: str) -> str:
        return ""

    def get_host_header_conditions(self, listener_arn: str, target_group_arn: str) -> list:
        rules = self.evlb_client.describe_rules(ListenerArn=listener_arn)["Rules"]

        for rule in rules:
            for action in rule["Actions"]:
                if action["Type"] == "forward" and action["TargetGroupArn"] == target_group_arn:
                    conditions = rule["Conditions"]

        # filter to host-header conditions
        conditions = [
            {i: condition[i] for i in condition if i != "Values"}
            for condition in conditions
            if condition["Field"] == "host-header"
        ]

        # remove internal hosts
        conditions[0]["HostHeaderConfig"]["Values"] = [
            v for v in conditions[0]["HostHeaderConfig"]["Values"]
        ]

        return conditions

    def get_rules_tag_descriptions_by_listener_arn(self, listener_arn: str) -> list:
        rules = self.evlb_client.describe_rules(ListenerArn=listener_arn)["Rules"]
        return self.get_rules_tag_descriptions(rules)

    def get_rules_tag_descriptions(self, rules: list) -> list:
        tag_descriptions = []
        chunk_size = 20

        for i in range(0, len(rules), chunk_size):
            chunk = rules[i : i + chunk_size]
            resource_arns = [r["RuleArn"] for r in chunk]
            response = self.evlb_client.describe_tags(ResourceArns=resource_arns)
            tag_descriptions.extend(response["TagDescriptions"])

        return tag_descriptions

    def create_header_rule(
        self,
        listener_arn: str,
        target_group_arn: str,
        header_name: str,
        values: list,
        rule_name: str,
        priority: int,
        conditions: list,
    ):
        pass

    def create_source_ip_rule(
        self,
        listener_arn: str,
        target_group_arn: str,
        values: list,
        rule_name: str,
        priority: int,
        conditions: list,
    ):
        pass


def get_load_balancer_for_application(session: boto3.Session, app: str, env: str) -> str:
    lb_client = session.client("elbv2")

    describe_response = lb_client.describe_load_balancers()
    load_balancers = [lb["LoadBalancerArn"] for lb in describe_response["LoadBalancers"]]

    load_balancers = lb_client.describe_tags(ResourceArns=load_balancers)["TagDescriptions"]

    load_balancer_arn = None
    for lb in load_balancers:
        tags = {t["Key"]: t["Value"] for t in lb["Tags"]}
        if tags.get("copilot-application") == app and tags.get("copilot-environment") == env:
            load_balancer_arn = lb["ResourceArn"]

    if not load_balancer_arn:
        raise LoadBalancerNotFoundException(
            f"No load balancer found for {app} in the {env} environment"
        )

    return load_balancer_arn


def get_https_listener_for_application(session: boto3.Session, app: str, env: str) -> str:
    load_balancer_arn = get_load_balancer_for_application(session, app, env)
    lb_client = session.client("elbv2")
    listeners = lb_client.describe_listeners(LoadBalancerArn=load_balancer_arn)["Listeners"]

    listener_arn = None

    try:
        listener_arn = next(l["ListenerArn"] for l in listeners if l["Protocol"] == "HTTPS")
    except StopIteration:
        pass

    if not listener_arn:
        raise ListenerNotFoundException(f"No HTTPS listener for {app} in the {env} environment")

    return listener_arn


def get_https_certificate_for_application(session: boto3.Session, app: str, env: str) -> str:

    listener_arn = get_https_listener_for_application(session, app, env)
    cert_client = session.client("elbv2")
    certificates = cert_client.describe_listener_certificates(ListenerArn=listener_arn)[
        "Certificates"
    ]

    try:
        certificate_arn = next(c["CertificateArn"] for c in certificates if c["IsDefault"])
    except StopIteration:
        raise CertificateNotFoundException(env)

    return certificate_arn


class LoadBalancerException(PlatformException):
    pass


class LoadBalancerNotFoundException(LoadBalancerException):
    pass


class ListenerNotFoundException(LoadBalancerException):
    pass


class ListenerRuleNotFoundException(LoadBalancerException):
    pass


class CertificateNotFoundException(PlatformException):
    def __init__(self, environment_name: str):
        super().__init__(
            f"""No certificate found with domain name matching environment {environment_name}."."""
        )
