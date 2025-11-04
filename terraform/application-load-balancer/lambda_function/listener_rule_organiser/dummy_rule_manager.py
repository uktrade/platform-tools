from rule_manager import RuleManager

DUMMY_RULES_RANGE_START = 1000


class DummyRuleManager(RuleManager):
    def __init__(self, application, environment, listener_arn):
        super().__init__(application, environment, listener_arn)

        self._cached_rules = None

    @property
    def dummy_rules(self):
        if self._cached_rules is not None:
            return self._cached_rules

        self._cached_rules = [
            r
            for r in self.rules.values()
            if "reason" in r["Tags"] and r["Tags"]["reason"] == "DummyRule"
        ]

        return self._cached_rules

    def create_rules(self, parameters):
        if parameters.service_name in [r["Tags"]["service"] for r in self.dummy_rules]:
            print(f"service {parameters.service_name} already has a dummy rule, exiting")
            return

        next_priority = DUMMY_RULES_RANGE_START

        if self.dummy_rules:
            next_priority = max([int(r["Priority"]) for r in self.dummy_rules]) + 1

        print(f"creating dummy rule with priority {next_priority}")

        self.get_client().create_rule(
            ListenerArn=self.listener_arn,
            Conditions=[
                {
                    "Field": "host-header",
                    "HostHeaderConfig": {"Values": [f"{parameters.service_name}.dummy"]},
                }
            ],
            Priority=next_priority,
            Actions=[
                {
                    "Type": "forward",
                    "TargetGroupArn": parameters.target_group,
                }
            ],
            Tags=[
                {
                    "Key": "application",
                    "Value": self.application,
                },
                {
                    "Key": "environment",
                    "Value": self.environment,
                },
                {
                    "Key": "service",
                    "Value": parameters.service_name,
                },
                {
                    "Key": "managed-by",
                    "Value": "DBT Platform - Service Terraform",
                },
                {
                    "Key": "reason",
                    "Value": "DummyRule",
                },
            ],
        )

    def delete_rules(self, parameters):
        rule = next((r for r in self.dummy_rules if r["Tags"]["service"] == parameters.service_name), None)

        if rule is None:
            print(f"service {parameters.service_name} does not have a dummy rule, exiting")
            return

        self.get_client().delete_rule(RuleArn=rule["RuleArn"])
