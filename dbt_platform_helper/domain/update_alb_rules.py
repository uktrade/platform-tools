import copy
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import List

from dbt_platform_helper.constants import COPILOT_RULE_PRIORITY
from dbt_platform_helper.constants import MAINTENANCE_PAGE_TAGS
from dbt_platform_helper.constants import MANAGED_BY_PLATFORM
from dbt_platform_helper.constants import MANAGED_BY_SERVICE_TERRAFORM
from dbt_platform_helper.constants import PLATFORM_RULE_STARTING_PRIORITY
from dbt_platform_helper.constants import RULE_PRIORITY_INCREMENT
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.load_balancers import LoadBalancerProvider
from dbt_platform_helper.utils.application import load_application


class RollbackException(PlatformException):
    pass


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


@dataclass
class OperationState:
    created_rules: List[str] = field(default_factory=list)
    deleted_rules: List[object] = field(default_factory=list)
    listener_arn: str = ""


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

        operation_state = OperationState(
            # created_rules=[],
            # deleted_rules=[],
        )

        try:
            self._execute_rule_updates(environment, operation_state)
        except Exception as e:
            self.io.error(f"Error during rule update: {str(e)}")
            self.io.warn("Rolling back")
            if operation_state.created_rules or operation_state.deleted_rules:
                self.io.info("Attempting to rollback changes ...")
                try:
                    self._rollback_changes(operation_state)
                except RollbackException as rollback_error:
                    raise PlatformException(f"Rollback failed: \n{str(rollback_error)}")
            else:
                raise

        if operation_state.created_rules:
            self.io.info(f"Created rules: {operation_state.created_rules}")
        if operation_state.deleted_rules:
            self.io.info(f"Deleted rules: {operation_state.deleted_rules}")

    def _execute_rule_updates(self, environment: str, operation_state: OperationState):
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

        operation_state.listener_arn = listener_arn

        self.io.info(f"ARN: {listener_arn}")

        rules = self.load_balancer.get_rules_with_tags_by_listener_arn(listener_arn)

        mapped_rules = {
            rule_type: [rule for rule in rules if self._filter_rule_type(rule) == rule_type]
            for rule_type in set(self._filter_rule_type(rule) for rule in rules)
        }

        if mapped_rules.get(RuleType.MANUAL.value, []):
            rule_arns = [rule["RuleArn"] for rule in mapped_rules[RuleType.MANUAL.value]]
            message = f"""The following rules have been created manually please review and if required set 
            the rules priority to the copilot range after priority: {COPILOT_RULE_PRIORITY}.\n
            Rules: {rule_arns}"""
            raise PlatformException(message)

        if (
            service_deployment_mode == Deployment.PLATFORM.value
            or service_deployment_mode == Deployment.DUAL_DEPLOY_PLATFORM.value
        ):

            # Clear out any platform rules which may be floating
            self._delete_rules(mapped_rules.get(RuleType.PLATFORM.value, []), operation_state)
            grouped = dict()

            service_mapped_tgs = self._get_tg_arns_for_platform_services(
                application_name, environment
            )
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

                service_name = self._get_service_from_tg(copilot_rule)

                tg_arn = service_mapped_tgs[service_name]

                actions = self._create_new_actions(copilot_rule["Actions"], tg_arn)
                self.io.info(f"Updated forward action for service {service_name} to use: {tg_arn}")
                if grouped.get(",".join(sorted_hosts)):
                    grouped[",".join(sorted_hosts)].append(
                        {
                            "copilot_rule": rule_arn,
                            "actions": actions,
                            "conditions": list_conditions,
                            "depth": depth,
                            "service_name": service_name,
                        }
                    )
                else:
                    grouped[",".join(sorted_hosts)] = [
                        {
                            "copilot_rule": rule_arn,
                            "actions": actions,
                            "conditions": list_conditions,
                            "depth": depth,
                            "service_name": service_name,
                        }
                    ]

            rule_priority = PLATFORM_RULE_STARTING_PRIORITY

            for hosts, rules in grouped.items():
                rules.sort(key=lambda x: x["depth"], reverse=True)

                for rule in rules:
                    # Create rule with priority
                    copilot_rule = rule.get("copilot_rule", "")
                    self.io.info(
                        f"Creating platform rule for corresponding copilot rule: {copilot_rule}"
                    )

                    rule_arn = self.load_balancer.create_rule(
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
                    )["Rules"][0]["RuleArn"]
                    operation_state.created_rules.append(rule_arn)
                    rule_priority += RULE_PRIORITY_INCREMENT

                next_thousandth = lambda x: ((x // 1000) + 1) * 1000
                rule_priority = next_thousandth(rule_priority)

        if (
            service_deployment_mode == Deployment.COPILOT.value
            or service_deployment_mode == Deployment.DUAL_DEPLOY_COPILOT.value
        ):
            self._delete_rules(mapped_rules.get(RuleType.PLATFORM.value, []), operation_state)

    def _delete_rules(self, rules, operation_state: OperationState):
        for rule in rules:
            rule_arn = rule["RuleArn"]
            try:

                operation_state.deleted_rules.append(
                    self.load_balancer.delete_listener_rule_by_resource_arn(rule_arn)
                )
                self.io.info(f"Deleted existing rule: {rule_arn}")
            except Exception as e:
                self.io.error(f"Failed to delete existing rule {rule_arn}: {str(e)}")
                raise

    def _filter_rule_type(self, rule):
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

    def _get_service_from_tg(self, rule):
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
        return None

    def _get_tg_arns_for_platform_services(
        self, application, environment, managed_by=MANAGED_BY_SERVICE_TERRAFORM
    ):
        tgs = self.load_balancer.get_target_groups_with_tags([])
        service_mapped_tgs = {}
        for tg in tgs:
            if (
                tg["Tags"].get("application", "") == application
                and tg["Tags"].get("environment", "") == environment
                and tg["Tags"].get("managed-by", "") == managed_by
            ):
                if tg["Tags"].get("service", ""):
                    service_mapped_tgs[tg["Tags"].get("service")] = tg["TargetGroupArn"]
                else:
                    tg_name = tg["TargetGroupName"]
                    self.io.warn(f"Target group {tg_name} has no 'service' tag")
        return service_mapped_tgs

    def _create_new_actions(self, actions, tg_arn):

        updated_actions = copy.deepcopy(actions)
        for action in updated_actions:
            if action.get("Type") == "forward" and "TargetGroupArn" in action:
                action["TargetGroupArn"] = tg_arn
                action.pop("ForwardConfig", None)
        return updated_actions

    def _rollback_changes(self, operation_state: OperationState) -> bool:
        rollback_errors = []
        delete_rollbacks = []
        create_rollbacks = []
        for rule_arn in operation_state.created_rules:
            try:
                self.io.debug(f"Rolling back: Deleting created rule {rule_arn}")
                delete_rollbacks.append(
                    self.load_balancer.delete_listener_rule_by_resource_arn(rule_arn)
                )
            except Exception as e:
                error_msg = f"Failed to delete rule {rule_arn} during rollback: {str(e)}"
                rollback_errors.append(error_msg)

        for rule_snapshot in operation_state.deleted_rules:
            try:
                self.io.debug(f"Rolling back: Recreating deleted rule {rule_snapshot.rule_arn}")

                create_rollbacks.append(
                    self.load_balancer.create_rule(
                        operation_state.listener_arn,
                    )["Rules"][
                        0
                    ]["RuleArn"]
                )
            except Exception as e:
                error_msg = (
                    f"Failed to recreate rule {rule_snapshot.rule_arn} during rollback: {str(e)}"
                )
                rollback_errors.append(error_msg)

        if rollback_errors:
            self.io.warn("Some rollback operations failed. Manual intervention may be required.")
            errors = "\n".join(rollback_errors)
            raise RollbackException(f"Rollback partially failed: {errors}")
        else:
            self.io.info("Rollback completed successfully")
            raise PlatformException(
                f"Rolledback rules by creating: {create_rollbacks} \n and deleting {delete_rollbacks}"
            )
