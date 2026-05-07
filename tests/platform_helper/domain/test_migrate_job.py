from unittest.mock import Mock

import boto3
from moto import mock_aws
import pytest

from dbt_platform_helper.platform_exception import PlatformException



class NewScheduleNotFoundException(PlatformException):
    pass

class OldScheduleNotFoundException(PlatformException):
    pass

class ScheduleMigrator:
    def __init__(self, old_scheduler_client, new_scheduler_client=None):
        self.old_scheduler_client = old_scheduler_client
        self.new_scheduler_client = new_scheduler_client

    def disable_old_schedule(self, name, environment):
        schedule = self.old_scheduler_client.get_schedule(Name=name, GroupName="default")
        self.old_scheduler_client.update_schedule(
            Name=schedule["Name"],
            GroupName=schedule["GroupName"],
            FlexibleTimeWindow=schedule["FlexibleTimeWindow"],
            Target=schedule["Target"],
            ScheduleExpression=schedule["ScheduleExpression"],
            State="DISABLED",
        )

    def enable_old_schedule(self, name, environment):
        schedule = self.old_scheduler_client.get_schedule(Name=name, GroupName="default")
        self.old_scheduler_client.update_schedule(
            Name=schedule["Name"],
            GroupName=schedule["GroupName"],
            FlexibleTimeWindow=schedule["FlexibleTimeWindow"],
            Target=schedule["Target"],
            ScheduleExpression=schedule["ScheduleExpression"],
            State="ENABLED",
        )

    def get_old_schedule(self, name, environment):
        schedule = self.old_scheduler_client.get_schedule(Name=name, GroupName="default")
        if schedule.get("State") == "ENABLED":
            return schedule.get("ScheduleExpression")
        else:
            return None

    def get_new_schedule(self, name, environment):
        rule = self.new_scheduler_client.describe_rule(Name=name)
        if rule.get("State") == "ENABLED":
            return rule.get("ScheduleExpression")
        else:
            return None
        
    def enable_new_schedule(self, name, environment):
        self.new_scheduler_client.enable_rule(Name=name)
        
    def disable_new_schedule(self, name, environment):
        self.new_scheduler_client.disable_rule(Name=name)
        
    def migrate_schedule(self, name, env):
        try:
            self.get_new_schedule(name, env)
        except Exception:
            raise NewScheduleNotFoundException(f"No new schedule to migrate to.  Ensure job {name} is deployed to {env}")
        
        
        self.disable_old_schedule(name, env)
        self.enable_new_schedule(name, env)
        
    def undo_migrate_schedule(self, name, env):
        try:
            self.get_old_schedule(name, env)
        except Exception:
            raise OldScheduleNotFoundException(f"No old schedule to revert to.  Leaving new schedule enabled")
        
        self.disable_new_schedule(name, env)
        self.enable_old_schedule(name, env)


@mock_aws
def test_get_old_schedule():
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

    result = ScheduleMigrator(client).get_old_schedule("my-enabled-rule", "dev")

    assert result == "rate(5 minutes)"


@mock_aws
def test_disable_old_schedule():
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

    ScheduleMigrator(client).disable_old_schedule("my-rule", "dev")

    result = ScheduleMigrator(client).get_old_schedule("my-rule", "dev")

    assert result is None


@mock_aws
def test_enable_old_schedule():
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

    assert ScheduleMigrator(client).get_old_schedule("my-job", "dev") is None

    ScheduleMigrator(client).enable_old_schedule("my-job", "dev")

    result = ScheduleMigrator(client).get_old_schedule("my-job", "dev")

    assert result == "rate(5 minutes)"


@mock_aws
def test_get_new_schedule():
    client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="ENABLED",
    )

    result = ScheduleMigrator(Mock(), client).get_new_schedule("my-job", "dev")

    assert result == "rate(5 minutes)"
    

@mock_aws
def test_enable_new_schedule():
    client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="DISABLED",
    )
    
    migrator = ScheduleMigrator(Mock(), client)

    assert migrator.get_new_schedule("my-job", "dev") is None
    
    migrator.enable_new_schedule("my-job", "dev")
    
    result = migrator.get_new_schedule("my-job", "dev")

    assert result == "rate(5 minutes)"
    
@mock_aws
def test_disable_new_schedule():
    client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="ENABLED",
    )

    migrator = ScheduleMigrator(Mock(), client)
    
    assert migrator.get_new_schedule("my-job", "dev") == "rate(5 minutes)"
    
    migrator.disable_new_schedule("my-job", "dev")
    
    result = migrator.get_new_schedule("my-job", "dev")

    assert result is None
    
@mock_aws
def test_migrate_schedule():
    old_client = boto3.client("scheduler", region_name="eu-west-2")
    new_client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    old_client.create_schedule(
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
    new_client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="DISABLED",
    )
    
    migrator = ScheduleMigrator(old_client, new_client)

    assert migrator.get_old_schedule("my-job", "dev") == "rate(5 minutes)"
    assert migrator.get_new_schedule("my-job", "dev") is None
    
    migrator.migrate_schedule("my-job", "dev")
    
    assert migrator.get_new_schedule("my-job", "dev") == "rate(5 minutes)"
    assert migrator.get_old_schedule("my-job", "dev") is None
    
@mock_aws
def test_undo_migrate_schedule():
    old_client = boto3.client("scheduler", region_name="eu-west-2")
    new_client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    old_client.create_schedule(
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
    new_client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="ENABLED",
    )
    
    migrator = ScheduleMigrator(old_client, new_client)

    assert migrator.get_new_schedule("my-job", "dev") == "rate(5 minutes)"
    assert migrator.get_old_schedule("my-job", "dev") is None
    
    migrator.undo_migrate_schedule("my-job", "dev")
    
    assert migrator.get_old_schedule("my-job", "dev") == "rate(5 minutes)"
    assert migrator.get_new_schedule("my-job", "dev") is None
    
@mock_aws
def test_migrate_fails_if_no_new_schedule():
    old_client = boto3.client("scheduler", region_name="eu-west-2")
    new_client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    old_client.create_schedule(
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
    
    migrator = ScheduleMigrator(old_client, new_client)

    with pytest.raises(NewScheduleNotFoundException) as e:
        migrator.migrate_schedule("my-job", "dev")
    
    assert "No new schedule to migrate to.  Ensure job my-job is deployed to dev" in str(e.value)
    

@mock_aws
def test_undo_migrate_fails_if_no_old_schedule():
    old_client = boto3.client("scheduler", region_name="eu-west-2")
    new_client = boto3.client("events", region_name="eu-west-2")
    test_rule = "my-job"
    new_client.put_rule(
        Name=test_rule,
        ScheduleExpression="rate(5 minutes)",
        State="ENABLED",
    )
    
    migrator = ScheduleMigrator(old_client, new_client)

    with pytest.raises(OldScheduleNotFoundException) as e:
        migrator.undo_migrate_schedule("my-job", "dev")
    
    assert "No old schedule to revert to.  Leaving new schedule enabled" in str(e.value)