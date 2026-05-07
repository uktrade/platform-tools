from unittest.mock import Mock

import boto3
import pytest
from moto import mock_aws

from dbt_platform_helper.platform_exception import PlatformException


class NewScheduleNotFoundException(PlatformException):
    pass


class OldScheduleNotFoundException(PlatformException):
    pass

class TooManyOldScheduledJobsFoundException(PlatformException):
    pass


class ScheduleMigrator:
    def __init__(self, application, old_scheduler_client, new_scheduler_client=None):
        self.application = application
        self.old_scheduler_client = old_scheduler_client
        self.new_scheduler_client = new_scheduler_client

    def disable_new_schedule(self, name, environment):
        schedule = self.new_scheduler_client.get_schedule(Name=name, GroupName="default")
        self.new_scheduler_client.update_schedule(
            Name=schedule["Name"],
            GroupName=schedule["GroupName"],
            FlexibleTimeWindow=schedule["FlexibleTimeWindow"],
            Target=schedule["Target"],
            ScheduleExpression=schedule["ScheduleExpression"],
            State="DISABLED",
        )

    def enable_new_schedule(self, name, environment):
        schedule = self.new_scheduler_client.get_schedule(Name=name, GroupName="default")
        self.new_scheduler_client.update_schedule(
            Name=schedule["Name"],
            GroupName=schedule["GroupName"],
            FlexibleTimeWindow=schedule["FlexibleTimeWindow"],
            Target=schedule["Target"],
            ScheduleExpression=schedule["ScheduleExpression"],
            State="ENABLED",
        )

    def get_new_schedule(self, name, environment):
        schedule = self.new_scheduler_client.get_schedule(Name=name, GroupName="default")
        if schedule.get("State") == "ENABLED":
            return schedule.get("ScheduleExpression")
        else:
            return None

    def get_old_schedule(self, name, environment):
        rule = self.old_scheduler_client.describe_rule(Name=name)
        if rule.get("State") == "ENABLED":
            return rule.get("ScheduleExpression")
        else:
            return None

    def enable_old_schedule(self, name, environment):
        self.old_scheduler_client.enable_rule(Name=name)

    def disable_old_schedule(self, name, environment):
        self.old_scheduler_client.disable_rule(Name=name)

    def migrate_schedule(self, name, env):
        try:
            self.get_new_schedule(name, env)
        except Exception:
            raise NewScheduleNotFoundException(
                f"No new schedule to migrate to.  Ensure job {name} is deployed to {env}"
            )

        self.disable_old_schedule(name, env)
        self.enable_new_schedule(name, env)

    def undo_migrate_schedule(self, name, env):
        try:
            self.get_old_schedule(name, env)
        except Exception:
            raise OldScheduleNotFoundException(
                f"No old schedule to revert to.  Leaving new schedule enabled"
            )

        self.disable_new_schedule(name, env)
        self.enable_old_schedule(name, env)
        
    def get_new_schedule_name(self, name, env):
        return f"{self.application}-{env}-{name}-schedule"
    
    def get_old_schedule_name(self, name, env):
        REQUIRED_TAGS = {
            "copilot-application": self.application,
            "copilot-environment": env,
            "copilot-service": name,
        }
        paginator = self.old_scheduler_client.get_paginator("list_rules")
        matching_rules = []
        for page in paginator.paginate():
            for rule in page["Rules"]:
                arn = rule["Arn"]
                tags_response = self.old_scheduler_client.list_tags_for_resource(ResourceARN=arn)
                
                tags = {
                    tag["Key"]: tag["Value"]
                    for tag in tags_response.get("Tags", [])
                }
                
                if all(tags.get(k) == v for k, v in REQUIRED_TAGS.items()):
                    matching_rules.append(rule)
        
        if len(matching_rules)==1:
            return matching_rules[0].get("Name")
        if not matching_rules:
            raise OldScheduleNotFoundException(f"{name} could not be found in the {env} environment")
        else:
            raise TooManyOldScheduledJobsFoundException(f"A unique job {name} could not be found in the {env} environment")


def test_get_new_schedule_name():
    result = ScheduleMigrator("demodjango", Mock(), Mock()).get_new_schedule_name("my-enabled-rule", "dev")

    assert result == "demodjango-dev-my-enabled-rule-schedule"


@mock_aws
def test_get_old_schedule_name():
    client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job-XYZ"
    client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="DISABLED",
        Tags=[
            {
                "Key": "copilot-application",
                "Value": "demodjango"
            },
            {
                "Key": "copilot-environment",
                "Value": "dev"
            },
            {
                "Key": "copilot-service",
                "Value": "my-job"
            },
         ],
    )
    result = ScheduleMigrator("demodjango", client, Mock()).get_old_schedule_name("my-job", "dev")

    assert result == "my-job-XYZ"
    
@mock_aws
def test_get_old_schedule_raises_if_tags_dont_match():
    client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job-XYZ"
    client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="DISABLED",
        Tags=[
            {
                "Key": "copilot-application",
                "Value": "something else"
            },
            {
                "Key": "copilot-environment",
                "Value": "dev"
            },
            {
                "Key": "copilot-service",
                "Value": "my-job"
            },
         ],
    )
    with pytest.raises(OldScheduleNotFoundException) as e:
        result = ScheduleMigrator("demodjango", client, Mock()).get_old_schedule_name("my-job", "dev")

    assert "my-job could not be found in the dev environment" in str(e.value)
    
@mock_aws
def test_get_old_schedule_raises_if_tags_not_unique():
    client = boto3.client("events", region_name="eu-west-2")
    client.put_rule(
        Name="my-job-XYZ",
        ScheduleExpression="rate(5 minutes)",
        State="DISABLED",
        Tags=[
            {
                "Key": "copilot-application",
                "Value": "demodjango"
            },
            {
                "Key": "copilot-environment",
                "Value": "dev"
            },
            {
                "Key": "copilot-service",
                "Value": "my-job"
            },
         ],
    )
    client.put_rule(
        Name="my-job-123",
        ScheduleExpression="rate(5 minutes)",
        State="DISABLED",
        Tags=[
            {
                "Key": "copilot-application",
                "Value": "demodjango"
            },
            {
                "Key": "copilot-environment",
                "Value": "dev"
            },
            {
                "Key": "copilot-service",
                "Value": "my-job"
            },
         ],
    )
    with pytest.raises(TooManyOldScheduledJobsFoundException) as e:
        result = ScheduleMigrator("demodjango", client, Mock()).get_old_schedule_name("my-job", "dev")

    assert "A unique job my-job could not be found in the dev environment" in str(e.value)


@mock_aws
def test_get_new_schedule():
    client = boto3.client("scheduler", region_name="eu-west-2")
    test_rule = "my-enabled-rule"
    client.create_schedule(
        Name=test_rule,
        GroupName="default",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": "arn:aws:states:eu-west-2:123456789012:stateMachine:dummy",
            "RoleArn": "arn:aws:iam::123456789012:role/dummy",
        },
        ScheduleExpression="rate(5 minutes)",
        State="ENABLED",
    )

    result = ScheduleMigrator("demodjango", Mock(), client).get_new_schedule(
        "my-enabled-rule", "dev"
    )

    assert result == "rate(5 minutes)"


@mock_aws
def test_disable_new_schedule():
    client = boto3.client("scheduler", region_name="eu-west-2")
    test_rule = "my-rule"
    client.create_schedule(
        Name=test_rule,
        GroupName="default",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": "arn:aws:states:eu-west-2:123456789012:stateMachine:dummy",
            "RoleArn": "arn:aws:iam::123456789012:role/dummy",
        },
        ScheduleExpression="rate(5 minutes)",
        State="ENABLED",
    )

    migrator = ScheduleMigrator("demodjango", Mock(), client)

    migrator.disable_new_schedule("my-rule", "dev")

    result = migrator.get_new_schedule("my-rule", "dev")

    assert result is None


@mock_aws
def test_enable_new_schedule():
    client = boto3.client("scheduler", region_name="eu-west-2")
    test_rule = "my-job"
    client.create_schedule(
        Name=test_rule,
        GroupName="default",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": "arn:aws:states:eu-west-2:123456789012:stateMachine:dummy",
            "RoleArn": "arn:aws:iam::123456789012:role/dummy",
        },
        ScheduleExpression="rate(5 minutes)",
        State="DISABLED",
    )

    migrator = ScheduleMigrator("demodjango", Mock(), client)

    assert migrator.get_new_schedule("my-job", "dev") is None

    migrator.enable_new_schedule("my-job", "dev")

    result = migrator.get_new_schedule("my-job", "dev")

    assert result == "rate(5 minutes)"


@mock_aws
def test_get_old_schedule():
    client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="ENABLED",
    )

    result = ScheduleMigrator("demodjango", client, Mock()).get_old_schedule("my-job", "dev")

    assert result == "rate(5 minutes)"


@mock_aws
def test_enable_old_schedule():
    client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="DISABLED",
    )

    migrator = ScheduleMigrator("demodjango", client, Mock())

    assert migrator.get_old_schedule("my-job", "dev") is None

    migrator.enable_old_schedule("my-job", "dev")

    result = migrator.get_old_schedule("my-job", "dev")

    assert result == "rate(5 minutes)"


@mock_aws
def test_disable_old_schedule():
    client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="ENABLED",
    )

    migrator = ScheduleMigrator("demodjango", client, Mock())

    assert migrator.get_old_schedule("my-job", "dev") == "rate(5 minutes)"

    migrator.disable_old_schedule("my-job", "dev")

    result = migrator.get_old_schedule("my-job", "dev")

    assert result is None


@mock_aws
def test_migrate_schedule():
    new_client = boto3.client("scheduler", region_name="eu-west-2")
    old_client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    new_client.create_schedule(
        Name=test_rule,
        GroupName="default",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": "arn:aws:states:eu-west-2:123456789012:stateMachine:dummy",
            "RoleArn": "arn:aws:iam::123456789012:role/dummy",
        },
        ScheduleExpression="rate(5 minutes)",
        State="DISABLED",
    )
    old_client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="ENABLED",
    )

    migrator = ScheduleMigrator("demodjango", old_client, new_client)

    assert migrator.get_old_schedule("my-job", "dev") == "rate(5 minutes)"
    assert migrator.get_new_schedule("my-job", "dev") is None

    migrator.migrate_schedule("my-job", "dev")

    assert migrator.get_new_schedule("my-job", "dev") == "rate(5 minutes)"
    assert migrator.get_old_schedule("my-job", "dev") is None


@mock_aws
def test_undo_migrate_schedule():
    new_client = boto3.client("scheduler", region_name="eu-west-2")
    old_client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    new_client.create_schedule(
        Name=test_rule,
        GroupName="default",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": "arn:aws:states:eu-west-2:123456789012:stateMachine:dummy",
            "RoleArn": "arn:aws:iam::123456789012:role/dummy",
        },
        ScheduleExpression="rate(5 minutes)",
        State="ENABLED",
    )
    old_client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="DISABLED",
    )

    migrator = ScheduleMigrator("demodjango", old_client, new_client)

    assert migrator.get_new_schedule("my-job", "dev") == "rate(5 minutes)"
    assert migrator.get_old_schedule("my-job", "dev") is None

    migrator.undo_migrate_schedule("my-job", "dev")

    assert migrator.get_old_schedule("my-job", "dev") == "rate(5 minutes)"
    assert migrator.get_new_schedule("my-job", "dev") is None


@mock_aws
def test_migrate_fails_if_no_new_schedule():
    new_client = boto3.client("scheduler", region_name="eu-west-2")
    old_client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    old_client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="ENABLED",
    )

    migrator = ScheduleMigrator("demodjango", old_client, new_client)

    with pytest.raises(NewScheduleNotFoundException) as e:
        migrator.migrate_schedule("my-job", "dev")

    assert "No new schedule to migrate to.  Ensure job my-job is deployed to dev" in str(e.value)


@mock_aws
def test_undo_migrate_fails_if_no_old_schedule():
    new_client = boto3.client("scheduler", region_name="eu-west-2")
    old_client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    new_client.create_schedule(
        Name=test_rule,
        GroupName="default",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": "arn:aws:states:eu-west-2:123456789012:stateMachine:dummy",
            "RoleArn": "arn:aws:iam::123456789012:role/dummy",
        },
        ScheduleExpression="rate(5 minutes)",
        State="ENABLED",
    )

    migrator = ScheduleMigrator("demodjango", old_client, new_client)

    with pytest.raises(OldScheduleNotFoundException) as e:
        migrator.undo_migrate_schedule("my-job", "dev")

    assert "No old schedule to revert to.  Leaving new schedule enabled" in str(e.value)
