class Vpc:
    def __init__(self, subnets: list[str], security_groups: list[str]):
        self.subnets = subnets
        self.security_groups = security_groups
