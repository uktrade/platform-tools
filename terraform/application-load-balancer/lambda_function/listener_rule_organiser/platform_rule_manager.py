from rule_manager import RuleManager

PLATFORM_RULES_RANGE_START = 1000

class PlatformRuleManager(RuleManager):
    def __init__(self, application, environment, listener_arn):
        super().__init__(application, environment, listener_arn)

        self._cached_rules = None
