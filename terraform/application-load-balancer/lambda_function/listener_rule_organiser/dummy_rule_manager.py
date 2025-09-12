import boto3

DUMMY_RULES_RANGE_START = 1000


class DummyRuleManager:
    def __init__(self, application, environment, listener_arn):
        self.client = None
        self.application = application
        self.environment = environment
        self.listener_arn = listener_arn
        self._cached_rules = None

    def get_client(self):
        if self.client is None:
            self.client = boto3.client("elbv2")
        return self.client

    @property
    def rules(self):
        if self._cached_rules is not None:
            return self._cached_rules

        print(f"pulling list of current dummy rules from {self.listener_arn}")

        # Get a list of all rules on the listener
        current_rules = {}
        rules_paginator = self.get_client().get_paginator("describe_rules")

        for rule_page in rules_paginator.paginate(ListenerArn=self.listener_arn):
            for rule in rule_page["Rules"]:
                current_rules[rule["RuleArn"]] = rule

        # Hydrate listener rule tags
        rule_tag_chunks = list(create_chunk_iterator([r for r in current_rules.keys()], 20))
        for rule_tag_chunk in rule_tag_chunks:
            tags_response = self.get_client().describe_tags(ResourceArns=rule_tag_chunk)
            for tags in tags_response["TagDescriptions"]:
                # Turn the tags list into a dict for easy queries
                current_rules[tags["ResourceArn"]]["Tags"] = {
                    item["Key"]: item["Value"] for item in tags["Tags"]
                }

        self._cached_rules = [
            r
            for r in current_rules.values()
            if "reason" in r["Tags"] and r["Tags"]["reason"] == "DummyRule"
        ]

        return self._cached_rules

    def create_dummy_rule(self, target_group_arn, service_name):
        if service_name in [r["Tags"]["service"] for r in self.rules]:
            print(f"service {service_name} already has a dummy rule, exiting")
            return

        next_priority = DUMMY_RULES_RANGE_START

        if self.rules:
            next_priority = max([int(r["Priority"]) for r in self.rules]) + 1

        print(f"creating dummy rule with priority {next_priority}")

        self.get_client().create_rule(
            ListenerArn=self.listener_arn,
            Conditions=[
                {
                    "Field": "host-header",
                    "HostHeaderConfig": {"Values": [f"{service_name}.dummy"]},
                }
            ],
            Priority=next_priority,
            Actions=[
                {
                    "Type": "forward",
                    "TargetGroupArn": target_group_arn,
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
                    "Value": service_name,
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

    def delete_dummy_rule(self, service_name):
        rule = next((r for r in self.rules if r["Tags"]["service"] == service_name), None)

        if rule is None:
            print(f"service {service_name} does not have a dummy rule, exiting")
            return

        self.get_client().delete_rule(RuleArn=rule["RuleArn"])


def create_chunk_iterator(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]
