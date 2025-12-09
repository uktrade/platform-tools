from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import List

from botocore.exceptions import ClientError

from dbt_platform_helper.constants import COPILOT_RULE_PRIORITY
from dbt_platform_helper.constants import DUMMY_RULE_REASON
from dbt_platform_helper.constants import HTTP_SERVICE_TYPES
from dbt_platform_helper.constants import MAINTENANCE_PAGE_REASON
from dbt_platform_helper.constants import MANAGED_BY_PLATFORM
from dbt_platform_helper.constants import MANAGED_BY_SERVICE_TERRAFORM
from dbt_platform_helper.constants import PLATFORM_RULE_STARTING_PRIORITY
from dbt_platform_helper.constants import RULE_PRIORITY_INCREMENT
from dbt_platform_helper.domain.service import ServiceManager
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
    DUMMY = "dummy"


class Deployment(Enum):
    PLATFORM = "platform"
    COPILOT = "copilot"
    DUAL_DEPLOY_PLATFORM = "dual-deploy-platform-traffic"
    DUAL_DEPLOY_COPILOT = "dual-deploy-copilot-traffic"


@dataclass
class OperationState:
    created_rules: List[object] = field(default_factory=list)
    deleted_rules: List[object] = field(default_factory=list)
    updated_rules: List[object] = field(default_factory=list)
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
        self.load_balancer: LoadBalancerProvider = load_balancer_p(session, io=self.io)

    def update_alb_rules(
        self,
        environment: str,
    ):
        """
        Change ALB rules for a given environment.

        Attempt to rollback the rules created/deleted if a failure occurs.
        """

        operation_state = OperationState()

        try:
            self._execute_rule_updates(environment, operation_state)
            if operation_state.created_rules:
                self.io.info(f"Created rules: {len(operation_state.created_rules)}")
                self._output_rule_changes(operation_state.created_rules)
            if operation_state.deleted_rules:
                self.io.info(f"Deleted rules: {len(operation_state.deleted_rules)}")
                self._output_rule_changes(operation_state.deleted_rules)
        except Exception as e:
            if operation_state.created_rules or operation_state.deleted_rules:
                self.io.error(f"Error during rule update: {str(e)}")
                self.io.warn("Rolling back")
                self.io.info("Attempting to rollback changes ...")
                try:
                    self._rollback_changes(operation_state)
                except RollbackException as rollback_error:
                    raise PlatformException(f"Rollback failed: \n{str(rollback_error)}")
            else:
                raise

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

        self.io.debug(f"Listener ARN: {listener_arn}")

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
            service_models = ServiceManager().get_service_models(application, environment)
            grouped = defaultdict(list)

            for service in service_models:
                if service.type not in HTTP_SERVICE_TYPES:
                    continue

                aliases = (
                    [service.http.alias]
                    if isinstance(service.http.alias, str)
                    else service.http.alias
                )

                additional_rules = getattr(service.http, "additional_rules", None)
                if additional_rules:
                    for rule in additional_rules:
                        additional_aliases = (
                            [rule.alias] if isinstance(rule.alias, str) else rule.alias
                        )
                        grouped[(service.name, rule.path)].extend(additional_aliases)

                grouped[(service.name, service.http.path)].extend(aliases)

            rules = []
            for (name, path), aliases in grouped.items():
                path_pattern = ["/*"] if path == "/" else [path, f"{path}/*"]
                condition_length = len(aliases) + len(path_pattern)

                # AWS allows a maximum of 5 condition values per rule, this includes host and path values
                max_conditions = 5
                if condition_length > max_conditions:
                    i = 0
                    while i < condition_length:
                        remaining_slots = max_conditions - len(path_pattern)
                        alias_split = aliases[i : i + remaining_slots] if aliases else []
                        if not alias_split:
                            break

                        rules.append(
                            {
                                "service": name,
                                "path": path,
                                "path_pattern": path_pattern,
                                "aliases": sorted(set(alias_split)),
                            }
                        )
                        i += remaining_slots
                else:
                    rules.append(
                        {
                            "service": name,
                            "path": path,
                            "path_pattern": path_pattern,
                            "aliases": sorted(set(aliases)),
                        }
                    )

            rules.sort(
                key=lambda r: (len([s for s in r["path"].split("/") if s]), r["aliases"]),
                reverse=True,
            )

            service_mapped_tgs = self._get_tg_arns_for_platform_services(
                application_name, environment
            )

            platform_rules = mapped_rules.get(RuleType.PLATFORM.value, [])

            rule_priority = PLATFORM_RULE_STARTING_PRIORITY
            for rule in rules:
                actions = [
                    {"Type": "forward", "TargetGroupArn": service_mapped_tgs[rule["service"]]}
                ]
                conditions = [
                    {"Field": "host-header", "HostHeaderConfig": {"Values": rule["aliases"]}},
                    {
                        "Field": "path-pattern",
                        "PathPatternConfig": {"Values": rule["path_pattern"]},
                    },
                ]
                tags = [
                    {"Key": "application", "Value": application_name},
                    {"Key": "environment", "Value": environment},
                    {"Key": "service", "Value": rule["service"]},
                    {"Key": "reason", "Value": "service"},
                    {"Key": "managed-by", "Value": MANAGED_BY_PLATFORM},
                ]

                try:
                    rule = self.load_balancer.create_rule(
                        listener_arn,
                        actions,
                        conditions,
                        rule_priority,
                        tags,
                    )["Rules"][0]
                    rule_arn = rule["RuleArn"]

                    if rule_arn in [rule["RuleArn"] for rule in platform_rules]:
                        operation_state.updated_rules.append(rule)
                    else:
                        operation_state.created_rules.append(rule)

                except ClientError as e:
                    if e.response["Error"]["Code"] == "PriorityInUse":
                        existing_rule = [
                            r for r in platform_rules if r["Priority"] == str(rule_priority)
                        ]
                        if not existing_rule:
                            raise PlatformException(
                                f"Priority {rule_priority} in use but no matching platform rule found."
                            )

                        self._delete_rules(existing_rule, operation_state)

                        rule = self.load_balancer.create_rule(
                            listener_arn,
                            actions,
                            conditions,
                            rule_priority,
                            tags,
                        )["Rules"][0]

                        operation_state.created_rules.append(rule)
                    else:
                        raise

                rule_priority += RULE_PRIORITY_INCREMENT

            # Remove dangling rules
            managed_rules = [
                rule["RuleArn"]
                for rules in [
                    operation_state.created_rules,
                    operation_state.updated_rules,
                    operation_state.deleted_rules,
                ]
                for rule in rules
            ]

            for rule in platform_rules:
                if rule["RuleArn"] not in managed_rules:
                    self._delete_rules([rule], operation_state)

        # Remove dummy rules
        if service_deployment_mode == Deployment.PLATFORM.value:
            self._delete_rules(mapped_rules.get(RuleType.DUMMY.value, []), operation_state)

        if (
            service_deployment_mode == Deployment.COPILOT.value
            or service_deployment_mode == Deployment.DUAL_DEPLOY_COPILOT.value
        ):
            self._delete_rules(mapped_rules.get(RuleType.PLATFORM.value, []), operation_state)

    def _delete_rules(self, rules: List[dict], operation_state: OperationState):
        for rule in rules:
            rule_arn = rule["RuleArn"]
            try:
                self.load_balancer.delete_listener_rule_by_resource_arn(rule_arn)
                operation_state.deleted_rules.append(rule)
                self.io.debug(f"Deleted existing rule: {rule_arn}")
            except Exception as e:
                self.io.error(f"Failed to delete existing rule {rule_arn}: {str(e)}")
                raise

    def _filter_rule_type(self, rule: dict) -> str:
        if rule["Tags"]:
            if rule["Tags"].get("managed-by", "") == MANAGED_BY_PLATFORM:
                return RuleType.PLATFORM.value
            if rule["Tags"].get("reason", None) == MAINTENANCE_PAGE_REASON:
                return RuleType.MAINTENANCE.value
            if rule["Tags"].get("reason", None) == DUMMY_RULE_REASON:
                return RuleType.DUMMY.value

        if rule["Priority"] == "default":
            return RuleType.DEFAULT.value
        if int(rule["Priority"]) >= COPILOT_RULE_PRIORITY:
            return RuleType.COPILOT.value

        return RuleType.MANUAL.value

    def _get_tg_arns_for_platform_services(
        self, application: str, environment: str, managed_by: str = MANAGED_BY_SERVICE_TERRAFORM
    ) -> dict:
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

    def _rollback_changes(self, operation_state: OperationState):
        rollback_errors = []
        delete_rollbacks = []
        create_rollbacks = []
        for rule in operation_state.created_rules:
            rule_arn = rule["RuleArn"]
            try:
                self.io.debug(f"Rolling back: Deleting created rule {rule_arn}")
                self.load_balancer.delete_listener_rule_by_resource_arn(rule_arn)
                delete_rollbacks.append(rule_arn)
            except Exception as e:
                error_msg = f"Failed to delete rule {rule_arn} during rollback: {str(e)}"
                rollback_errors.append(error_msg)

        for rule_snapshot in operation_state.deleted_rules:
            rule_arn = rule_snapshot["RuleArn"]
            try:
                self.io.debug(f"Rolling back: Recreating deleted rule {rule_arn}")
                create_rollbacks.append(
                    self.load_balancer.create_rule(
                        operation_state.listener_arn,
                        actions=rule_snapshot["Actions"],
                        conditions=[
                            {"Field": key, "Values": value}
                            for key, value in rule_snapshot["Conditions"].items()
                        ],
                        priority=int(rule_snapshot["Priority"]),
                        tags=[
                            {"Key": key, "Value": value}
                            for key, value in rule_snapshot["Tags"].items()
                        ],
                    )["Rules"][0]["RuleArn"]
                )
            except Exception as e:
                error_msg = f"Failed to recreate rule {rule_arn} during rollback: {str(e)}"
                rollback_errors.append(error_msg)

        if rollback_errors:
            self.io.warn("Some rollback operations failed. Manual intervention may be required.")
            errors = "\n".join(rollback_errors)
            raise RollbackException(f"Rollback partially failed: {errors}")
        else:
            self.io.info("Rollback completed successfully")
            self.io.info(
                f"Rolled back rules by creating: {create_rollbacks} \n and deleting {delete_rollbacks}"
            )

    def _output_rule_changes(self, rules):
        for rule in rules:
            hosts = []
            paths = []

            conditions = rule.get("Conditions", [])
            if isinstance(conditions, list):
                for condition in conditions:
                    if condition["Field"] == "host-header":
                        hosts.extend(condition["HostHeaderConfig"]["Values"])
                    elif condition["Field"] == "path-pattern":
                        paths.extend(condition["PathPatternConfig"]["Values"])
            elif isinstance(conditions, dict):
                hosts.extend(conditions.get("host-header"))
                paths.extend(conditions.get("path-pattern"))

            rule_arn = rule["RuleArn"]
            priority = rule["Priority"]
            hosts = ",".join(hosts)
            paths = ",".join(paths)
            self.io.info(f"ARN: {rule_arn}")
            self.io.info(f"Priority: {priority}")
            self.io.info(f"Hosts: {hosts}")
            self.io.info(f"Paths: {paths}\n")
