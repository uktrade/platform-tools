from boto3 import Session

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.aws import get_aws_session_or_abort


def normalise_to_cidr(ip: str):
    if "/" in ip:
        return ip
    SINGLE_IPV4_CIDR_PREFIX_LENGTH = "32"
    return f"{ip}/{SINGLE_IPV4_CIDR_PREFIX_LENGTH}"


class LoadBalancerProvider:

    def __init__(self, session: Session = None, io: ClickIOProvider = ClickIOProvider()):
        self.session = session
        self.evlb_client = self._get_client("elbv2")
        self.rg_tagging_client = self._get_client("resourcegroupstaggingapi")
        self.io = io

    def _get_client(self, client: str):
        if not self.session:
            self.session = get_aws_session_or_abort()
        return self.session.client(client)

    def find_target_group(self, app: str, env: str, svc: str) -> str:
        target_group_arn = None

        response = self.rg_tagging_client.get_resources(
            TagFilters=[
                {
                    "Key": "copilot-application",
                    "Values": [
                        app,
                    ],
                    "Key": "copilot-environment",
                    "Values": [
                        env,
                    ],
                    "Key": "copilot-service",
                    "Values": [
                        svc,
                    ],
                },
            ],
            ResourceTypeFilters=[
                "elasticloadbalancing:targetgroup",
            ],
        )  # TODO: DBTP-1942: should be paginated
        for resource in response["ResourceTagMappingList"]:
            tags = {tag["Key"]: tag["Value"] for tag in resource["Tags"]}

            if (
                "copilot-service" in tags
                and tags["copilot-service"] == svc
                and "copilot-environment" in tags
                and tags["copilot-environment"] == env
                and "copilot-application" in tags
                and tags["copilot-application"] == app
            ):
                target_group_arn = resource["ResourceARN"]

        if not target_group_arn:
            self.io.error(
                f"No target group found for application: {app}, environment: {env}, service: {svc}",
            )

        return target_group_arn

    def get_https_certificate_for_application(self, app: str, env: str) -> str:
        listener_arn = self.get_https_listener_for_application(app, env)
        certificates = self.evlb_client.describe_listener_certificates(ListenerArn=listener_arn)[
            "Certificates"
        ]  # TODO: DBTP-1942: should be paginated

        try:
            certificate_arn = next(c["CertificateArn"] for c in certificates if c["IsDefault"])
        except StopIteration:
            raise CertificateNotFoundException(env)

        return certificate_arn

    def get_https_listener_for_application(self, app: str, env: str) -> str:
        load_balancer_arn = self.get_load_balancer_for_application(app, env)

        listeners = self.evlb_client.describe_listeners(LoadBalancerArn=load_balancer_arn)[
            "Listeners"
        ]  # TODO: DBTP-1942: should be paginated

        listener_arn = None

        try:
            listener_arn = next(l["ListenerArn"] for l in listeners if l["Protocol"] == "HTTPS")
        except StopIteration:
            pass

        if not listener_arn:
            raise ListenerNotFoundException(app, env)

        return listener_arn

    def get_load_balancer_for_application(self, app: str, env: str) -> str:
        describe_response = self.evlb_client.describe_load_balancers()
        load_balancers = [lb["LoadBalancerArn"] for lb in describe_response["LoadBalancers"]]

        tag_descriptions = []
        for i in range(0, len(load_balancers), 20):
            chunk = load_balancers[i : i + 20]
            tag_descriptions.extend(
                self.evlb_client.describe_tags(ResourceArns=chunk)["TagDescriptions"]
            )

        for lb in tag_descriptions:
            tags = {t["Key"]: t["Value"] for t in lb["Tags"]}
            # TODO: DBTP-1967: copilot hangover, creates coupling to specific tags could update to check application and environment
            if tags.get("copilot-application") == app and tags.get("copilot-environment") == env:
                return lb["ResourceArn"]

        raise LoadBalancerNotFoundException(app, env)

    def get_host_header_conditions(self, listener_arn: str, target_group_arn: str) -> list:
        rules = self.evlb_client.describe_rules(ListenerArn=listener_arn)[
            "Rules"
        ]  # TODO: DBTP-1942: should be paginated

        conditions = []

        for rule in rules:
            for action in rule["Actions"]:
                if action["Type"] == "forward" and action["TargetGroupArn"] == target_group_arn:
                    conditions = rule["Conditions"]

        if not conditions:
            raise ListenerRuleConditionsNotFoundException(listener_arn)

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
        rules = self.evlb_client.describe_rules(ListenerArn=listener_arn)[
            "Rules"
        ]  # TODO: DBTP-1942: should be paginated
        return self.get_rules_tag_descriptions(rules)

    def get_rules_tag_descriptions(self, rules: list) -> list:
        tag_descriptions = []
        chunk_size = 20

        for i in range(0, len(rules), chunk_size):
            chunk = rules[i : i + chunk_size]
            resource_arns = [r["RuleArn"] for r in chunk]
            response = self.evlb_client.describe_tags(
                ResourceArns=resource_arns
            )  # TODO should be paginated
            tag_descriptions.extend(response["TagDescriptions"])

        return tag_descriptions

    def create_rule(
        self,
        listener_arn: str,
        actions: list,
        conditions: list,
        priority: int,
        tags: list,
    ):
        return self.evlb_client.create_rule(
            ListenerArn=listener_arn,
            Priority=priority,
            Conditions=conditions,
            Actions=actions,
            Tags=tags,
        )

    def create_forward_rule(
        self,
        listener_arn: str,
        target_group_arn: str,
        rule_name: str,
        priority: int,
        conditions: list,
        additional_tags: list = [],
    ):
        return self.create_rule(
            listener_arn=listener_arn,
            priority=priority,
            conditions=conditions,
            actions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
            tags=[{"Key": "name", "Value": rule_name}, *additional_tags],
        )

    def create_header_rule(
        self,
        listener_arn: str,
        target_group_arn: str,
        header_name: str,
        values: list,
        rule_name: str,
        priority: int,
        conditions: list,
        additional_tags: list = [],
    ):

        combined_conditions = [
            {
                "Field": "http-header",
                "HttpHeaderConfig": {"HttpHeaderName": header_name, "Values": values},
            }
        ] + conditions

        self.create_forward_rule(
            listener_arn,
            target_group_arn,
            rule_name,
            priority,
            combined_conditions,
            additional_tags,
        )

        self.io.debug(
            f"Creating listener rule {rule_name} for HTTPS Listener with arn {listener_arn}.\nIf request header {header_name} contains one of the values {values}, the request will be forwarded to target group with arn {target_group_arn}.\n\n",
        )

    def create_source_ip_rule(
        self,
        listener_arn: str,
        target_group_arn: str,
        values: list,
        rule_name: str,
        priority: int,
        conditions: list,
        additional_tags: list = [],
    ):
        combined_conditions = [
            {
                "Field": "source-ip",
                "SourceIpConfig": {"Values": [normalise_to_cidr(value) for value in values]},
            }
        ] + conditions

        self.create_forward_rule(
            listener_arn,
            target_group_arn,
            rule_name,
            priority,
            combined_conditions,
            additional_tags,
        )

        self.io.debug(
            f"Creating listener rule {rule_name} for HTTPS Listener with arn {listener_arn}.\nIf request source ip matches one of the values {values}, the request will be forwarded to target group with arn {target_group_arn}.\n\n",
        )

    def delete_listener_rule_by_tags(self, tag_descriptions: list, tag_name: str) -> list:
        deleted_rules = []

        for description in tag_descriptions:
            tags = {t["Key"]: t["Value"] for t in description["Tags"]}
            if tags.get("name") == tag_name:
                if description["ResourceArn"]:
                    self.evlb_client.delete_rule(RuleArn=description["ResourceArn"])
                    deleted_rules.append(description)

        return deleted_rules


class LoadBalancerException(PlatformException):
    pass


class LoadBalancerNotFoundException(LoadBalancerException):
    def __init__(self, application_name, env):
        super().__init__(
            f"No load balancer found for environment {env} in the application {application_name}."
        )


class ListenerNotFoundException(LoadBalancerException):
    def __init__(self, application_name, env):
        super().__init__(
            f"No HTTPS listener found for environment {env} in the application {application_name}."
        )


class ListenerRuleNotFoundException(LoadBalancerException):
    pass


class ListenerRuleConditionsNotFoundException(LoadBalancerException):
    def __init__(self, listener_arn):
        super().__init__(f"No listener rule conditions found for listener ARN: {listener_arn}")


class CertificateNotFoundException(PlatformException):
    def __init__(self, environment_name: str):
        super().__init__(
            f"""No certificate found with domain name matching environment {environment_name}."."""
        )
