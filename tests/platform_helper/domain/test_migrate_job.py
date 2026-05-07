from unittest.mock import Mock

import boto3
from moto import mock_aws


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

    assert ScheduleMigrator(Mock(), client).get_new_schedule("my-job", "dev") is None
    
    ScheduleMigrator(Mock(), client).enable_new_schedule("my-job", "dev")
    
    result = ScheduleMigrator(Mock(), client).get_new_schedule("my-job", "dev")

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

    assert ScheduleMigrator(Mock(), client).get_new_schedule("my-job", "dev") == "rate(5 minutes)"
    
    ScheduleMigrator(Mock(), client).disable_new_schedule("my-job", "dev")
    
    result = ScheduleMigrator(Mock(), client).get_new_schedule("my-job", "dev")

    assert result is None
