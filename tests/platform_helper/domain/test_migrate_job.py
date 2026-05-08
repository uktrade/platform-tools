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
                tags_response = self.old_schedule_provider.client.list_tags_for_resource(ResourceARN=arn)
                
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
    result = ScheduleMigrator("demodjango", OldScheduleProvider(client), Mock()).get_old_schedule_name("my-job", "dev")

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
        result = ScheduleMigrator("demodjango", OldScheduleProvider(client), Mock()).get_old_schedule_name("my-job", "dev")

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
        result = ScheduleMigrator("demodjango", OldScheduleProvider(client), Mock()).get_old_schedule_name("my-job", "dev")

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

    result = ScheduleMigrator("demodjango", Mock(), NewScheduleProvider(client)).new_schedule_provider.get_schedule(
        "my-enabled-rule"
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

    migrator = ScheduleMigrator("demodjango", Mock(), NewScheduleProvider(client))

    migrator.new_schedule_provider.disable_schedule("my-rule")

    result = migrator.new_schedule_provider.get_schedule("my-rule")

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

    migrator = ScheduleMigrator("demodjango", Mock(), NewScheduleProvider(client))

    assert migrator.new_schedule_provider.get_schedule("my-job") is None

    migrator.new_schedule_provider.enable_schedule("my-job")

    result = migrator.new_schedule_provider.get_schedule("my-job")

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

    result = ScheduleMigrator("demodjango", OldScheduleProvider(client), Mock()).old_schedule_provider.get_schedule("my-job")

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

    migrator = ScheduleMigrator("demodjango", OldScheduleProvider(client), Mock())

    assert migrator.old_schedule_provider.get_schedule("my-job") is None

    migrator.old_schedule_provider.enable_schedule("my-job")

    result = migrator.old_schedule_provider.get_schedule("my-job")

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

    migrator = ScheduleMigrator("demodjango", OldScheduleProvider(client), Mock())

    assert migrator.old_schedule_provider.get_schedule("my-job") == "rate(5 minutes)"

    migrator.old_schedule_provider.disable_schedule("my-job")

    result = migrator.old_schedule_provider.get_schedule("my-job")

    assert result is None


@mock_aws
def test_migrate_schedule():
    new_client = boto3.client("scheduler", region_name="eu-west-2")
    old_client = boto3.client("events", region_name="eu-west-2")
    new_schedule_name = f"demodjango-dev-my-job-schedule"
    new_client.create_schedule(
        Name=new_schedule_name,
        GroupName="default",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": "arn:aws:states:eu-west-2:123456789012:stateMachine:dummy",
            "RoleArn": "arn:aws:iam::123456789012:role/dummy",
        },
        ScheduleExpression="rate(5 minutes)",
        State="DISABLED",
    )
    old_schedule_name = "old-rule-for-my-job"
    old_client.put_rule(
        Name=old_schedule_name,
        ScheduleExpression="rate(5 minutes)",
        State="ENABLED",
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

    migrator = ScheduleMigrator("demodjango", OldScheduleProvider(old_client), NewScheduleProvider(new_client))

    assert migrator.old_schedule_provider.get_schedule(old_schedule_name) == "rate(5 minutes)"
    assert migrator.new_schedule_provider.get_schedule(new_schedule_name) is None

    migrator.migrate_schedule("my-job", "dev")

    assert migrator.new_schedule_provider.get_schedule(new_schedule_name) == "rate(5 minutes)"
    assert migrator.old_schedule_provider.get_schedule(old_schedule_name) is None


@mock_aws
def test_undo_migrate_schedule():
    new_client = boto3.client("scheduler", region_name="eu-west-2")
    old_client = boto3.client("events", region_name="eu-west-2")
    new_schedule_name = f"demodjango-dev-my-job-schedule"
    old_schedule_name = "old-rule-for-my-job"
    new_client.create_schedule(
        Name=new_schedule_name,
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
        Name=old_schedule_name,
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

    migrator = ScheduleMigrator("demodjango", OldScheduleProvider(old_client), NewScheduleProvider(new_client))

    assert migrator.new_schedule_provider.get_schedule(new_schedule_name) == "rate(5 minutes)"
    assert migrator.old_schedule_provider.get_schedule(old_schedule_name) is None

    migrator.undo_migrate_schedule("my-job", "dev")

    assert migrator.old_schedule_provider.get_schedule(old_schedule_name) == "rate(5 minutes)"
    assert migrator.new_schedule_provider.get_schedule(new_schedule_name) is None


@mock_aws
def test_migrate_fails_if_no_new_schedule():
    new_client = boto3.client("scheduler", region_name="eu-west-2")
    old_client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    old_client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="ENABLED",
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

    migrator = ScheduleMigrator("demodjango", OldScheduleProvider(old_client), NewScheduleProvider(new_client))

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

    migrator = ScheduleMigrator("demodjango", OldScheduleProvider(old_client), NewScheduleProvider(new_client))

    with pytest.raises(OldScheduleNotFoundException) as e:
        migrator.undo_migrate_schedule("my-job", "dev")

    assert "my-job could not be found in the dev environment" in str(e.value)
