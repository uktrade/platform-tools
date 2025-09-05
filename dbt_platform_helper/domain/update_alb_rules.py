import copy

from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.load_balancers import LoadBalancerProvider
from dbt_platform_helper.utils.application import load_application


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
            .get("service-deployment-mode", "copilot")
        )

        self.io.info(f"Deployment Mode: {service_deployment_mode}")

        listener_arn = self.load_balancer.get_https_listener_for_application(
            application.name, environment
        )

        self.io.info(f"ARN: {listener_arn}")

        rules = self.load_balancer.get_rules_with_tags_by_listener_arn(listener_arn)

        # TODO move to constants
        copilot_rule_priority = 48000
        platform_rule_starting_priority = 10000

        def filter_rule_type(rule):
            maintenance_page_tags = [
                "MaintenancePage",
                "AllowedIps",
                "BypassIpFilter",
                "AllowedSourceIps",
            ]
            for tag in rule["Tags"]:
                if tag.get("Key", "") == "managed-by" and tag["Value"] == "DBT Platform":
                    return "platform"
                if tag.get("Key", "") == "name" and tag["Value"] in maintenance_page_tags:
                    return "maintenance"

            if rule["Priority"] == "default":
                return "default"
            if int(rule["Priority"]) >= copilot_rule_priority:
                return "copilot"

            return "manual"

        mapped_rules = {
            key: [rule for rule in rules if filter_rule_type(rule) == key]
            for key in set(filter_rule_type(rule) for rule in rules)
        }

        if mapped_rules["manual"]:
            rule_arns = [rule["RuleArn"] for rule in mapped_rules["manual"]]
            message = f"""The following rules have been created manually please review and if required set 
            the rules priority to the copilot range after priority: {copilot_rule_priority}.\n
            Rules: {rule_arns}"""
            self.io.abort_with_error(message)

        def extract_condition_information(conditions):
            paths = []
            hosts = []
            prepared_conditions = []
            for condition in conditions:
                field = condition.get("Field", "")
                values = condition.get("Values", [])
                sorted_values = tuple(sorted(values) if isinstance(values, list) else [values])

                if field == "host-header" and condition.get("HostHeaderConfig", None):
                    hosts = sorted_values
                    condition.pop("HostHeaderConfig")
                elif field == "path-pattern" and condition.get("PathPatternConfig", None):
                    paths = sorted_values
                    condition.pop("PathPatternConfig")
                prepared_conditions.append(condition)

            # Take the deepest depth for priority ordering
            depths = [len([sub_path for sub_path in path.split("/") if sub_path]) for path in paths]
            max_depth = max(depths)
            return (hosts, conditions, max_depth)

        def get_service_from_tg(rule):
            target_group_arn = ""

            for action in rule["Actions"]:
                if action["Type"] == "forward":
                    target_group_arn = action["TargetGroupArn"]

            if target_group_arn:
                tgs = self.load_balancer.get_target_groups_with_tags([target_group_arn])

                # Feels like I am making a lot of assumptions here so not robust enough
                for tg in tgs:
                    for tag in tg["Tags"]:
                        if tag["Key"] == "copilot-service":
                            return tag["Value"]
            else:
                # TODO add error handling if no target_group_arn
                self.io.warn("no target group found")
            return

        def get_tg_arns_for_platform_services(
            application, environment, managed_by="DBT Platform - Service Terraform"
        ):
            tgs = self.load_balancer.get_target_groups_with_tags([])

            service_mapped_tgs = {}
            for tg in tgs:

                tg_tags = {tag["Key"]: tag["Value"] for tag in tg["Tags"]}

                if tg_tags.get("environment") != environment:
                    continue

                if (
                    tg_tags.get("application") == application
                    and tg_tags.get("environment") == environment
                    and tg_tags.get("managed-by") == managed_by
                ):
                    service = tg_tags.get("service")
                    if service:
                        service_mapped_tgs[service] = tg["TargetGroupArn"]
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

        if service_deployment_mode == "platform" or "dual-deploy-platform-traffic":

            grouped = dict()

            service_mapped_tgs = get_tg_arns_for_platform_services(application_name, environment)

            for copilot_rule in mapped_rules.get("copilot", []):
                rule_arn = copilot_rule["RuleArn"]
                self.io.info(f"Building platform rule for corresponding copilot rule: {rule_arn}")
                hosts, conditions, depth = extract_condition_information(copilot_rule["Conditions"])

                service_name = get_service_from_tg(copilot_rule)

                tg_arn = service_mapped_tgs[service_name]

                actions = create_new_actions(copilot_rule["Actions"], tg_arn)
                self.io.info(f"Updated forward action for service {service_name} to use: {tg_arn}")
                if grouped.get(",".join(hosts)):
                    grouped[",".join(hosts)].append(
                        {
                            "actions": actions,
                            "conditions": conditions,
                            "depth": depth,
                            "service_name": service_name,
                        }
                    )
                else:
                    grouped[",".join(hosts)] = [
                        {
                            "actions": actions,
                            "conditions": conditions,
                            "depth": depth,
                            "service_name": service_name,
                        }
                    ]

                # TODO delete any existing platform rules before re-creating

            rule_priority = platform_rule_starting_priority

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
                            {"Key": "managed-by", "Value": "DBT Platform"},
                        ],
                    )
                    rule_priority += 100

                next_thousandth = lambda x: ((x // 1000) + 1) * 1000
                rule_priority = next_thousandth(rule_priority)

        # TODO if an expection occurs roll back?
        if (
            service_deployment_mode == "copilot"
            or service_deployment_mode == "dual-deploy-copilot-traffic"
        ):
            deleted_rules = []
            for rule in mapped_rules.get("platform", []):
                rule_arn = rule["RuleArn"]
                deleted_rules.append(
                    self.load_balancer.delete_listener_rule_by_resource_arn(rule_arn)
                )

            # TODO arns useless after being deleted
            # TODO show services arns were delted for but maybe normalise the data in mapped_rules first?
            self.io.info(f"Deleted rule arns: {deleted_rules}")
