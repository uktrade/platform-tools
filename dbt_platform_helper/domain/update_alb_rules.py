import copy
from enum import Enum

from dbt_platform_helper.constants import COPILOT_RULE_PRIORITY
from dbt_platform_helper.constants import MAINTENANCE_PAGE_TAGS
from dbt_platform_helper.constants import MANAGED_BY_PLATFORM
from dbt_platform_helper.constants import MANAGED_BY_SERVICE_TERRAFORM
from dbt_platform_helper.constants import PLATFORM_RULE_STARTING_PRIORITY
from dbt_platform_helper.constants import RULE_PRIORITY_INCREMENT
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.load_balancers import LoadBalancerProvider
from dbt_platform_helper.utils.application import load_application


class RuleType(Enum):
    PLATFORM = "platform"
    MAINTENANCE = "maintenance"
    DEFAULT = "default"
    COPILOT = "copilot"
    MANUAL = "manual"


class Deployment(Enum):
    PLATFORM = "platform"
    COPILOT = "copilot"
    DUAL_DEPLOY_PLATFORM = "dual-deploy-platform-traffic"
    DUAL_DEPLOY_COPILOT = "dual-deploy-copilot-traffic"


class UpdateALBRules:

    def __init__(
        self,
        session,
        config_provider: ConfigProvider = ConfigProvider(ConfigValidator()),
        io: ClickIOProvider = ClickIOProvider(),
        load_application=load_application,
        load_balancer_p: LoadBalancerProvider = LoadBalancerProvider,
    ):
        self.config_provider = config_provider
        self.io = io
        self.load_application = load_application
        self.load_balancer: LoadBalancerProvider = load_balancer_p(session)

    def update_alb_rules(
        self,
        environment: str,
    ):
        """"""
        platform_config = self.config_provider.get_enriched_config()

        application_name = platform_config.get("application", "")
        application = self.load_application(app=application_name)

        service_deployment_mode = (
            platform_config.get("environments")
            .get(environment, {})
            .get("service-deployment-mode", Deployment.COPILOT.value)
        )

        self.io.info(f"Deployment Mode: {service_deployment_mode}")

        listener_arn = self.load_balancer.get_https_listener_for_application(
            application.name, environment
        )

        self.io.info(f"ARN: {listener_arn}")

        rules = self.load_balancer.get_rules_with_tags_by_listener_arn(listener_arn)

        def filter_rule_type(rule):
            if rule["Tags"]:
                if rule["Tags"].get("managed-by", "") == MANAGED_BY_PLATFORM:
                    return RuleType.PLATFORM.value
                if rule["Tags"].get("name", "") in MAINTENANCE_PAGE_TAGS:
                    return RuleType.MAINTENANCE.value

            if rule["Priority"] == "default":
                return RuleType.DEFAULT.value
            if int(rule["Priority"]) >= COPILOT_RULE_PRIORITY:
                return RuleType.COPILOT.value

            return RuleType.MANUAL.value

        mapped_rules = {
            key: [rule for rule in rules if filter_rule_type(rule) == key]
            for key in set(filter_rule_type(rule) for rule in rules)
        }

        if mapped_rules.get(RuleType.MANUAL.value, ""):
            rule_arns = [rule["RuleArn"] for rule in mapped_rules[RuleType.MANUAL]]
            message = f"""The following rules have been created manually please review and if required set 
            the rules priority to the copilot range after priority: {COPILOT_RULE_PRIORITY}.\n
            Rules: {rule_arns}"""
            self.io.abort_with_error(message)

        def get_service_from_tg(rule):
            target_group_arn = ""

            # TODO normalise this?
            for action in rule["Actions"]:
                if action["Type"] == "forward":
                    target_group_arn = action["TargetGroupArn"]

            if target_group_arn:
                tgs = self.load_balancer.get_target_groups_with_tags([target_group_arn])

                # Feels like I am making a lot of assumptions here so not robust enough
                for tg in tgs:
                    return tg["Tags"].get("copilot-service", "")
            else:
                # TODO add error handling if no target_group_arn
                self.io.warn("no target group found")
            return

        def get_tg_arns_for_platform_services(
            application, environment, managed_by=MANAGED_BY_SERVICE_TERRAFORM
        ):
            tgs = self.load_balancer.get_target_groups_with_tags([])

            service_mapped_tgs = {}
            for tg in tgs:
                if tg["Tags"].get("environment") != environment:
                    continue

                if (
                    tg["Tags"].get("application", "") == application
                    and tg["Tags"].get("environment", "") == environment
                    and tg["Tags"].get("managed-by", "") == managed_by
                ):
                    if tg["Tags"].get("service", ""):
                        service_mapped_tgs[tg["Tags"].get("service")] = tg["TargetGroupArn"]
                    else:
                        tg_name = tg["name"]
                        self.io.warn(f"Target group {tg_name} has no 'service' tag")
            return service_mapped_tgs

        def create_new_actions(actions, tg_arn):

            updated_actions = copy.deepcopy(actions)
            for action in updated_actions:
                if action.get("Type") == "forward" and "TargetGroupArn" in action:
                    action["TargetGroupArn"] = tg_arn
                    action.pop("ForwardConfig")
            return updated_actions

        if (
            service_deployment_mode == Deployment.PLATFORM.value
            or service_deployment_mode == Deployment.DUAL_DEPLOY_PLATFORM.value
        ):

            grouped = dict()

            service_mapped_tgs = get_tg_arns_for_platform_services(application_name, environment)

            for copilot_rule in mapped_rules.get(RuleType.COPILOT.value, []):
                rule_arn = copilot_rule["RuleArn"]
                self.io.info(f"Building platform rule for corresponding copilot rule: {rule_arn}")
                sorted_hosts = sorted(copilot_rule["Conditions"].get("host-header", []))
                depth = max(
                    [
                        len([sub_path for sub_path in path.split("/") if sub_path])
                        for path in copilot_rule["Conditions"].get("path-pattern", [])
                    ]
                )
                list_conditions = [
                    {"Field": key, "Values": value}
                    for key, value in copilot_rule["Conditions"].items()
                ]

                service_name = get_service_from_tg(copilot_rule)

                tg_arn = service_mapped_tgs[service_name]

                actions = create_new_actions(copilot_rule["Actions"], tg_arn)
                self.io.info(f"Updated forward action for service {service_name} to use: {tg_arn}")
                if grouped.get(",".join(sorted_hosts)):
                    grouped[",".join(sorted_hosts)].append(
                        {
                            "actions": actions,
                            "conditions": list_conditions,
                            "depth": depth,
                            "service_name": service_name,
                        }
                    )
                else:
                    grouped[",".join(sorted_hosts)] = [
                        {
                            "actions": actions,
                            "conditions": list_conditions,
                            "depth": depth,
                            "service_name": service_name,
                        }
                    ]

                # TODO delete any existing platform rules before re-creating

            rule_priority = PLATFORM_RULE_STARTING_PRIORITY

            # TODO if an exception occurs rollback to all the conditions present before
            for hosts, rules in grouped.items():
                rules.sort(key=lambda x: x["depth"], reverse=True)

                for rule in rules:
                    # Create rule with priority
                    rule_arn = copilot_rule["RuleArn"]
                    self.io.info(
                        f"Creating platform rule for corresponding copilot rule: {rule_arn}"
                    )

                    self.load_balancer.create_rule(
                        listener_arn,
                        rule["actions"],
                        rule["conditions"],
                        rule_priority,
                        tags=[
                            {"Key": "application", "Value": application_name},
                            {"Key": "environment", "Value": environment},
                            {"Key": "service", "Value": rule["service_name"]},
                            {"Key": "reason", "Value": "service"},
                            {"Key": "managed-by", "Value": MANAGED_BY_PLATFORM},
                        ],
                    )
                    rule_priority += RULE_PRIORITY_INCREMENT

                next_thousandth = lambda x: ((x // 1000) + 1) * 1000
                rule_priority = next_thousandth(rule_priority)

        # TODO if an expection occurs roll back?
        if (
            service_deployment_mode == Deployment.COPILOT.value
            or service_deployment_mode == Deployment.DUAL_DEPLOY_COPILOT.value
        ):
            deleted_rules = []
            for rule in mapped_rules.get(RuleType.PLATFORM.value, []):
                rule_arn = rule["RuleArn"]
                deleted_rules.append(
                    self.load_balancer.delete_listener_rule_by_resource_arn(rule_arn)
                )

            # TODO arns useless after being deleted
            # TODO show services arns were delted for but maybe normalise the data in mapped_rules first?
            self.io.info(f"Deleted rule arns: {deleted_rules}")
