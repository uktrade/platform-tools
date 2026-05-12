from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider


class NewScheduleNotFoundException(PlatformException):
    pass


class OldScheduleNotFoundException(PlatformException):
    pass


class TooManyOldScheduledJobsFoundException(PlatformException):
    pass


class OldScheduleProvider:
    def __init__(self, event_client):
        self.client = event_client

    def get_schedule_expression(self, name):
        rule = self.client.describe_rule(Name=name)
        return rule.get("ScheduleExpression")

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
    def __init__(self, scheduler_client):
        self.client = scheduler_client

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
    def __init__(
        self,
        application: str,
        old_schedule_provider: OldScheduleProvider,
        new_schedule_provider: NewScheduleProvider,
        io: ClickIOProvider = None,
    ):
        self.application = application
        self.old_schedule_provider = old_schedule_provider
        self.new_schedule_provider = new_schedule_provider
        self.io = io or ClickIOProvider()

    def migrate_schedule(self, name, env):
        self.io.info(f"Beginning migration for job {name}. Checking initial conditions...")
        new_name = self.get_new_schedule_name(name, env)
        old_name = self.get_old_schedule_name(name, env)
        try:
            new_schedule = self.new_schedule_provider.get_schedule(new_name)
            self.io.info(f"New schedule is deployed to {env} environment.  Ready to migrate.")
        except Exception:
            raise NewScheduleNotFoundException(
                f"No new schedule to migrate to. Ensure job {name} is deployed to {env}"
            )

        old_schedule = self.old_schedule_provider.get_schedule(old_name)
        original_schedule_expression = self.old_schedule_provider.get_schedule_expression(old_name)

        if new_schedule and not old_schedule:

            if new_schedule == original_schedule_expression:
                self.io.abort_with_error("New schedule is already activated. Aborting.")
            else:
                self.io.info(
                    f"Updating new schedule from {new_schedule} to {original_schedule_expression} to match the original job"
                )
                self.new_schedule_provider.update_schedule(new_name, original_schedule_expression)
        else:
            self.io.info(
                f"Updating new schedule with old schedule expression {original_schedule_expression}."
            )
            self.new_schedule_provider.update_schedule(new_name, original_schedule_expression)
            self.old_schedule_provider.disable_schedule(old_name)
            self.new_schedule_provider.enable_schedule(new_name)
            self.io.info(
                f"Complete!  New schedule event {new_name} is enabled and old scheduled rule {old_name} is disabled"
            )

        self.io.info(
            f'\nPaste the following into service-manifest.yml schedule: "{original_schedule_expression}"'
        )

    def undo_migrate_schedule(self, name, env):
        self.io.info(f"Reverting migration for job {name}. Checking initial conditions...")
        new_name = self.get_new_schedule_name(name, env)
        old_name = self.get_old_schedule_name(name, env)

        self.new_schedule_provider.disable_schedule(new_name)
        self.old_schedule_provider.enable_schedule(old_name)
        self.io.info(
            f"Complete!  Old scheduled rule {old_name} is now enabled and new schedule event {new_name} is disabled"
        )

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
