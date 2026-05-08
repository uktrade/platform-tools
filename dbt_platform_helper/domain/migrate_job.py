from dbt_platform_helper.platform_exception import PlatformException


class NewScheduleNotFoundException(PlatformException):
    pass


class OldScheduleNotFoundException(PlatformException):
    pass


class TooManyOldScheduledJobsFoundException(PlatformException):
    pass


class OldScheduleProvider:
    def __init__(self, client):
        self.client = client

    def get_schedule(self, name):
        rule = self.client.describe_rule(Name=name)
        if rule.get("State") == "ENABLED":
            return rule.get("ScheduleExpression")
        else:
            return None

    def enable_schedule(self, name):
        self.client.enable_rule(Name=name)

    def disable_schedule(self, name):
        self.client.disable_rule(Name=name)


class NewScheduleProvider:
    def __init__(self, client):
        self.client = client

    def disable_schedule(self, name):
        schedule = self.client.get_schedule(Name=name, GroupName="default")
        self.client.update_schedule(
            Name=schedule["Name"],
            GroupName=schedule["GroupName"],
            FlexibleTimeWindow=schedule["FlexibleTimeWindow"],
            Target=schedule["Target"],
            ScheduleExpression=schedule["ScheduleExpression"],
            State="DISABLED",
        )

    def enable_schedule(self, name):
        schedule = self.client.get_schedule(Name=name, GroupName="default")
        self.client.update_schedule(
            Name=schedule["Name"],
            GroupName=schedule["GroupName"],
            FlexibleTimeWindow=schedule["FlexibleTimeWindow"],
            Target=schedule["Target"],
            ScheduleExpression=schedule["ScheduleExpression"],
            State="ENABLED",
        )

    def get_schedule(self, name):
        schedule = self.client.get_schedule(Name=name, GroupName="default")
        if schedule.get("State") == "ENABLED":
            return schedule.get("ScheduleExpression")
        else:
            return None
        
    def update_schedule(self, name, new_schedule):
        schedule = self.client.get_schedule(Name=name, GroupName="default")
        self.client.update_schedule(
            Name=schedule["Name"],
            GroupName=schedule["GroupName"],
            FlexibleTimeWindow=schedule["FlexibleTimeWindow"],
            Target=schedule["Target"],
            ScheduleExpression=new_schedule,
            State="ENABLED",
        )


class ScheduleMigrator:
    def __init__(self, application, old_schedule_provider, new_schedule_provider=None):
        self.application = application
        self.old_schedule_provider = old_schedule_provider
        self.new_schedule_provider = new_schedule_provider

    def migrate_schedule(self, name, env):
        new_name = self.get_new_schedule_name(name, env)
        old_name = self.get_old_schedule_name(name, env)
        try:
            self.new_schedule_provider.get_schedule(new_name)
        except Exception:
            raise NewScheduleNotFoundException(
                f"No new schedule to migrate to.  Ensure job {name} is deployed to {env}"
            )
            
        old_schedule = self.old_schedule_provider.get_schedule(old_name)
        self.new_schedule_provider.update_schedule(new_name, old_schedule)
        self.old_schedule_provider.disable_schedule(old_name)
        self.new_schedule_provider.enable_schedule(new_name)

    def undo_migrate_schedule(self, name, env):
        new_name = self.get_new_schedule_name(name, env)
        old_name = self.get_old_schedule_name(name, env)

        self.new_schedule_provider.disable_schedule(new_name)
        self.old_schedule_provider.enable_schedule(old_name)

    def get_new_schedule_name(self, name, env):
        return f"{self.application}-{env}-{name}-schedule"

    def get_old_schedule_name(self, name, env):
        REQUIRED_TAGS = {
            "copilot-application": self.application,
            "copilot-environment": env,
            "copilot-service": name,
        }
        paginator = self.old_schedule_provider.client.get_paginator("list_rules")
        matching_rules = []
        for page in paginator.paginate():
            for rule in page["Rules"]:
                arn = rule["Arn"]
                tags_response = self.old_schedule_provider.client.list_tags_for_resource(
                    ResourceARN=arn
                )

                tags = {tag["Key"]: tag["Value"] for tag in tags_response.get("Tags", [])}

                if all(tags.get(k) == v for k, v in REQUIRED_TAGS.items()):
                    matching_rules.append(rule)

        if len(matching_rules) == 1:
            return matching_rules[0].get("Name")
        if not matching_rules:
            raise OldScheduleNotFoundException(
                f"{name} could not be found in the {env} environment"
            )
        else:
            raise TooManyOldScheduledJobsFoundException(
                f"A unique job {name} could not be found in the {env} environment"
            )
