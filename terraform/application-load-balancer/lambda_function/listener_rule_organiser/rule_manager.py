import boto3


class RuleManager:
    def __init__(self, application, environment, listener_arn):
        self.client = None
        self.application = application
        self.environment = environment
        self.listener_arn = listener_arn

    def get_client(self):
        if self.client is None:
            self.client = boto3.client("elbv2")
        return self.client

    @property
    def rules(self):
        print(f"pulling list of current rules from {self.listener_arn}")

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

        return current_rules

    def create_rules(self, parameters):
        raise NotImplementedError("create_rules not implemented")

    def delete_rules(self, parameters):
        raise NotImplementedError("delete_rules not implemented")


def create_chunk_iterator(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i: i + n]
