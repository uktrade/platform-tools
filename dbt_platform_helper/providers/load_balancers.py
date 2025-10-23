import json
from typing import Dict
from typing import List

from boto3 import Session

from dbt_platform_helper.constants import MANAGED_BY_PLATFORM_TERRAFORM
from dbt_platform_helper.constants import ROUTED_TO_PLATFORM_MODES
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.parameter_store import ParameterStore
from dbt_platform_helper.utils.aws import get_aws_session_or_abort


def normalise_to_cidr(ip: str):
    if "/" in ip:
        return ip
    SINGLE_IPV4_CIDR_PREFIX_LENGTH = "32"
    return f"{ip}/{SINGLE_IPV4_CIDR_PREFIX_LENGTH}"


class ALBDataNormaliser:

    @staticmethod
    def tags_to_dict(tags: List[Dict[str, str]]) -> Dict[str, str]:
        return {tag.get("Key", ""): tag.get("Value", "") for tag in tags}

    @staticmethod
    def conditions_to_dict(conditions: List[Dict[str, List[str]]]) -> Dict[str, List[str]]:
        return {condition.get("Field", ""): condition.get("Values", "") for condition in conditions}


class LoadBalancerProvider:

    def __init__(self, session: Session = None, io: ClickIOProvider = ClickIOProvider()):
        self.session = session
        self.evlb_client = self._get_client("elbv2")
        self.rg_tagging_client = self._get_client("resourcegroupstaggingapi")
        self.parameter_store_provider = ParameterStore(self._get_client("ssm"))
        self.io = io

    def _get_client(self, client: str):
        if not self.session:
            self.session = get_aws_session_or_abort()
        return self.session.client(client)

    def find_target_group(self, app: str, env: str, svc: str) -> str:

        # TODO once copilot is gone this is no longer needed
        try:
            result = self.parameter_store_provider.get_ssm_parameter_by_name(
                f"/platform/applications/{app}/environments/{env}"
            )["Value"]
            env_config = json.loads(result)
            service_deployment_mode = env_config["service_deployment_mode"]
        except Exception:
            service_deployment_mode = "copilot"

        if service_deployment_mode in ROUTED_TO_PLATFORM_MODES:
            application_key = "application"
            environment_key = "environment"
            service_key = "service"
        else:
            application_key = "copilot-application"
            environment_key = "copilot-environment"
            service_key = "copilot-service"
        target_group_arn = None

        paginator = self.rg_tagging_client.get_paginator("get_resources")
        page_iterator = paginator.paginate(
            TagFilters=[
                {
                    "Key": application_key,
                    "Values": [
                        app,
                    ],
                },
                {
                    "Key": environment_key,
                    "Values": [
                        env,
                    ],
                },
                {
                    "Key": service_key,
                    "Values": [
                        svc,
                    ],
                },
            ],
            ResourceTypeFilters=[
                "elasticloadbalancing:targetgroup",
            ],
        )

        for page in page_iterator:
            for resource in page["ResourceTagMappingList"]:
                tags = {tag["Key"]: tag["Value"] for tag in resource["Tags"]}

                if (
                    tags.get(service_key) == svc
                    and tags.get(environment_key) == env
                    and tags.get(application_key) == app
                ):
                    target_group_arn = resource["ResourceARN"]

        if not target_group_arn:
            self.io.error(
                f"No target group found for application: {app}, environment: {env}, service: {svc}",
            )

        return target_group_arn

    def get_target_groups(self, target_group_arns: List[str]) -> List[dict]:
        tgs = []
        paginator = self.evlb_client.get_paginator("describe_target_groups")
        page_iterator = paginator.paginate(TargetGroupArns=target_group_arns)
        for page in page_iterator:
            tgs.extend(page["TargetGroups"])

        return tgs

    def get_target_groups_with_tags(
        self, target_group_arns: List[str], normalise: bool = True
    ) -> List[dict]:
        target_groups = self.get_target_groups(target_group_arns)

        tags = self.get_resources_tag_descriptions(target_groups, "TargetGroupArn")

        tgs_with_tags = self.merge_in_tags_by_resource_arn(target_groups, tags, "TargetGroupArn")

        if normalise:
            for tg in tgs_with_tags:
                tg["Tags"] = ALBDataNormaliser.tags_to_dict(tg["Tags"])
        return tgs_with_tags

    def get_https_certificate_for_listener(self, listener_arn: str, env: str):
        certificates = []
        paginator = self.evlb_client.get_paginator("describe_listener_certificates")
        page_iterator = paginator.paginate(ListenerArn=listener_arn)
        for page in page_iterator:
            certificates.extend(page["Certificates"])

        try:
            certificate_arn = next(c["CertificateArn"] for c in certificates if c["IsDefault"])
        except StopIteration:
            raise CertificateNotFoundException(env)

        return certificate_arn

    def get_https_certificate_for_application(self, app: str, env: str) -> str:
        listener_arn = self.get_https_listener_for_application(app, env)
        return self.get_https_certificate_for_listener(listener_arn, env)

    def get_listeners_for_load_balancer(self, load_balancer_arn: str) -> List[dict]:
        listeners = []
        paginator = self.evlb_client.get_paginator("describe_listeners")
        page_iterator = paginator.paginate(LoadBalancerArn=load_balancer_arn)
        for page in page_iterator:
            listeners.extend(page["Listeners"])

        return listeners

    def get_https_listener_for_application(self, app: str, env: str) -> str:
        load_balancer_arn = self.get_load_balancer_for_application(app, env)
        self.io.debug(f"Load Balancer ARN: {load_balancer_arn}")
        listeners = self.get_listeners_for_load_balancer(load_balancer_arn)

        listener_arn = None

        try:
            listener_arn = next(l["ListenerArn"] for l in listeners if l["Protocol"] == "HTTPS")
        except StopIteration:
            pass

        if not listener_arn:
            raise ListenerNotFoundException(app, env)

        return listener_arn

    def get_load_balancers(self) -> List[dict]:
        load_balancers = []
        paginator = self.evlb_client.get_paginator("describe_load_balancers")
        page_iterator = paginator.paginate()
        for page in page_iterator:
            load_balancers.extend(lb["LoadBalancerArn"] for lb in page["LoadBalancers"])

        return load_balancers

    def get_load_balancer_for_application(self, app: str, env: str) -> str:
        load_balancers = self.get_load_balancers()
        tag_descriptions = []
        for i in range(0, len(load_balancers), 20):
            chunk = load_balancers[i : i + 20]
            tag_descriptions.extend(
                self.evlb_client.describe_tags(ResourceArns=chunk)["TagDescriptions"]
            )  # describe_tags cannot be paginated - 04/04/2025

        for lb in tag_descriptions:
            tags = {t["Key"]: t["Value"] for t in lb["Tags"]}
            # TODO: DBTP-1967: copilot hangover, creates coupling to specific tags could update to check application and environment
            if (
                tags.get("copilot-application") == app
                and tags.get("copilot-environment") == env
                and tags.get("managed-by", "") == MANAGED_BY_PLATFORM_TERRAFORM
            ):
                return lb["ResourceArn"]

        raise LoadBalancerNotFoundException(app, env)

    def get_host_header_conditions(self, listener_arn: str, target_group_arn: str) -> list:
        rules = []
        paginator = self.evlb_client.get_paginator("describe_rules")
        page_iterator = paginator.paginate(ListenerArn=listener_arn)
        for page in page_iterator:
            rules.extend(page["Rules"])

        conditions = []

        for rule in rules:
            for action in rule["Actions"]:
                if "TargetGroupArn" in action:
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
        rules = self.get_listener_rules_by_listener_arn(listener_arn)

        return self.get_resources_tag_descriptions(rules)

    def merge_in_tags_by_resource_arn(
        self,
        resources: List[dict],
        tag_descriptions: List[dict],
        resources_identifier: str = "RuleArn",
    ):
        tags_by_resource_arn = {
            rule_tags.get("ResourceArn"): rule_tags for rule_tags in tag_descriptions if rule_tags
        }
        for resource in resources:
            tags = tags_by_resource_arn[resource[resources_identifier]]
            resource.update(tags)
        return resources

    def get_rules_with_tags_by_listener_arn(
        self, listener_arn: str, normalise: bool = True
    ) -> list:
        rules = self.get_listener_rules_by_listener_arn(listener_arn)

        tags = self.get_resources_tag_descriptions(rules)

        rules_with_tags = self.merge_in_tags_by_resource_arn(rules, tags)

        if normalise:
            for rule in rules_with_tags:
                rule["Conditions"] = ALBDataNormaliser.conditions_to_dict(rule["Conditions"])
                rule["Tags"] = ALBDataNormaliser.tags_to_dict(rule["Tags"])

        return rules_with_tags

    def get_listener_rules_by_listener_arn(self, listener_arn: str) -> list:
        rules = []
        paginator = self.evlb_client.get_paginator("describe_rules")
        page_iterator = paginator.paginate(ListenerArn=listener_arn)
        for page in page_iterator:
            rules.extend(page["Rules"])

        return rules

    def get_resources_tag_descriptions(
        self, resources: list, resource_identifier: str = "RuleArn"
    ) -> list:
        tag_descriptions = []
        chunk_size = 20

        for i in range(0, len(resources), chunk_size):
            chunk = resources[i : i + chunk_size]
            resource_arns = [r[resource_identifier] for r in chunk]
            response = self.evlb_client.describe_tags(
                ResourceArns=resource_arns
            )  # describe_tags cannot be paginated - 04/04/2025
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

    def delete_listener_rule_by_resource_arn(self, resource_arn: str) -> list:
        return self.evlb_client.delete_rule(RuleArn=resource_arn)


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
