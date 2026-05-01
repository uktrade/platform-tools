
import boto3
from moto import mock_aws


class ScheduleManager:
    def __init__(self, scheduler_client):
        self.scheduler_client = scheduler_client

    def disable_schedule(self, name, environment):
        schedule = self.scheduler_client.get_schedule(Name=name, GroupName="default")
        self.scheduler_client.update_schedule(
            Name=schedule["Name"],
            GroupName=schedule["GroupName"],
            FlexibleTimeWindow=schedule["FlexibleTimeWindow"],
            Target=schedule["Target"],
            ScheduleExpression=schedule["ScheduleExpression"],
            State="DISABLED",
        )

    def enable_schedule(self, name, environment):
        schedule = self.scheduler_client.get_schedule(Name=name, GroupName="default")
        self.scheduler_client.update_schedule(
            Name=schedule["Name"],
            GroupName=schedule["GroupName"],
            FlexibleTimeWindow=schedule["FlexibleTimeWindow"],
            Target=schedule["Target"],
            ScheduleExpression=schedule["ScheduleExpression"],
            State="ENABLED",
        )

    def get_schedule(self, name, environment):
        schedule = self.scheduler_client.get_schedule(Name=name, GroupName="default")
        if schedule.get("State") == "ENABLED":
            return schedule.get("ScheduleExpression")
        else:
            return None


@mock_aws
def test_get_schedule():
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

    result = ScheduleManager(client).get_schedule("my-enabled-rule", "dev")

    assert result == "rate(5 minutes)"


@mock_aws
def test_disable_schedule():
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

    ScheduleManager(client).disable_schedule("my-rule", "dev")

    result = ScheduleManager(client).get_schedule("my-rule", "dev")

    assert result is None


@mock_aws
def test_enable_schedule():
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

    assert ScheduleManager(client).get_schedule("my-job", "dev") is None

    ScheduleManager(client).enable_schedule("my-job", "dev")

    result = ScheduleManager(client).get_schedule("my-job", "dev")

    assert result == "rate(5 minutes)"
