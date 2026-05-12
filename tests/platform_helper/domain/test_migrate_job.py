from unittest.mock import Mock

import boto3
import pytest
from moto import mock_aws

from dbt_platform_helper.domain.migrate_job import NewScheduleNotFoundException
from dbt_platform_helper.domain.migrate_job import NewScheduleProvider
from dbt_platform_helper.domain.migrate_job import OldScheduleNotFoundException
from dbt_platform_helper.domain.migrate_job import OldScheduleProvider
from dbt_platform_helper.domain.migrate_job import ScheduleMigrator
from dbt_platform_helper.domain.migrate_job import TooManyOldScheduledJobsFoundException


def test_get_new_schedule_name():
    result = ScheduleMigrator("demodjango", Mock(), Mock()).get_new_schedule_name(
        "my-enabled-rule", "dev"
    )

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
            {"Key": "copilot-application", "Value": "demodjango"},
            {"Key": "copilot-environment", "Value": "dev"},
            {"Key": "copilot-service", "Value": "my-job"},
        ],
    )
    result = ScheduleMigrator(
        "demodjango", OldScheduleProvider(client), Mock()
    ).get_old_schedule_name("my-job", "dev")

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
            {"Key": "copilot-application", "Value": "something else"},
            {"Key": "copilot-environment", "Value": "dev"},
            {"Key": "copilot-service", "Value": "my-job"},
        ],
    )
    with pytest.raises(OldScheduleNotFoundException) as e:
        result = ScheduleMigrator(
            "demodjango", OldScheduleProvider(client), Mock()
        ).get_old_schedule_name("my-job", "dev")

    assert "my-job could not be found in the dev environment" in str(e.value)


@mock_aws
def test_get_old_schedule_raises_if_tags_not_unique():
    client = boto3.client("events", region_name="eu-west-2")
    client.put_rule(
        Name="my-job-XYZ",
        ScheduleExpression="rate(5 minutes)",
        State="DISABLED",
        Tags=[
            {"Key": "copilot-application", "Value": "demodjango"},
            {"Key": "copilot-environment", "Value": "dev"},
            {"Key": "copilot-service", "Value": "my-job"},
        ],
    )
    client.put_rule(
        Name="my-job-123",
        ScheduleExpression="rate(5 minutes)",
        State="DISABLED",
        Tags=[
            {"Key": "copilot-application", "Value": "demodjango"},
            {"Key": "copilot-environment", "Value": "dev"},
            {"Key": "copilot-service", "Value": "my-job"},
        ],
    )
    with pytest.raises(TooManyOldScheduledJobsFoundException) as e:
        result = ScheduleMigrator(
            "demodjango", OldScheduleProvider(client), Mock()
        ).get_old_schedule_name("my-job", "dev")

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

    result = ScheduleMigrator(
        "demodjango", Mock(), NewScheduleProvider(client)
    ).new_schedule_provider.get_schedule("my-enabled-rule")

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

    result = ScheduleMigrator(
        "demodjango", OldScheduleProvider(client), Mock()
    ).old_schedule_provider.get_schedule("my-job")

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
            {"Key": "copilot-application", "Value": "demodjango"},
            {"Key": "copilot-environment", "Value": "dev"},
            {"Key": "copilot-service", "Value": "my-job"},
        ],
    )

    migrator = ScheduleMigrator(
        "demodjango", OldScheduleProvider(old_client), NewScheduleProvider(new_client)
    )

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
            {"Key": "copilot-application", "Value": "demodjango"},
            {"Key": "copilot-environment", "Value": "dev"},
            {"Key": "copilot-service", "Value": "my-job"},
        ],
    )

    migrator = ScheduleMigrator(
        "demodjango", OldScheduleProvider(old_client), NewScheduleProvider(new_client)
    )

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
            {"Key": "copilot-application", "Value": "demodjango"},
            {"Key": "copilot-environment", "Value": "dev"},
            {"Key": "copilot-service", "Value": "my-job"},
        ],
    )

    migrator = ScheduleMigrator(
        "demodjango", OldScheduleProvider(old_client), NewScheduleProvider(new_client)
    )

    with pytest.raises(NewScheduleNotFoundException) as e:
        migrator.migrate_schedule("my-job", "dev")

    assert "No new schedule to migrate to. Ensure job my-job is deployed to dev" in str(e.value)


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

    migrator = ScheduleMigrator(
        "demodjango", OldScheduleProvider(old_client), NewScheduleProvider(new_client)
    )

    with pytest.raises(OldScheduleNotFoundException) as e:
        migrator.undo_migrate_schedule("my-job", "dev")

    assert "my-job could not be found in the dev environment" in str(e.value)


@mock_aws
def test_migrate_copies_old_schedule_to_new_schedule():
    DEFAULT_SCHEDULE = "rate(5 minutes)"
    ORIGINAL_SCHEDULE = "rate(10 minutes)"

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
        ScheduleExpression=DEFAULT_SCHEDULE,
        State="DISABLED",
    )
    old_client.put_rule(
        Name=old_schedule_name,
        ScheduleExpression=ORIGINAL_SCHEDULE,
        State="ENABLED",
        Tags=[
            {"Key": "copilot-application", "Value": "demodjango"},
            {"Key": "copilot-environment", "Value": "dev"},
            {"Key": "copilot-service", "Value": "my-job"},
        ],
    )

    migrator = ScheduleMigrator(
        "demodjango", OldScheduleProvider(old_client), NewScheduleProvider(new_client)
    )

    assert migrator.old_schedule_provider.get_schedule(old_schedule_name) == ORIGINAL_SCHEDULE
    assert migrator.new_schedule_provider.get_schedule(new_schedule_name) is None

    migrator.migrate_schedule("my-job", "dev")

    assert migrator.new_schedule_provider.get_schedule(new_schedule_name) == ORIGINAL_SCHEDULE
    assert migrator.old_schedule_provider.get_schedule(old_schedule_name) is None


@mock_aws
def test_migrate_fails_if_new_schedule_already_active(capsys):
    ORIGINAL_SCHEDULE = "rate(10 minutes)"

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
        ScheduleExpression=ORIGINAL_SCHEDULE,
        State="ENABLED",
    )
    old_client.put_rule(
        Name=old_schedule_name,
        ScheduleExpression=ORIGINAL_SCHEDULE,
        State="DISABLED",
        Tags=[
            {"Key": "copilot-application", "Value": "demodjango"},
            {"Key": "copilot-environment", "Value": "dev"},
            {"Key": "copilot-service", "Value": "my-job"},
        ],
    )

    migrator = ScheduleMigrator(
        "demodjango", OldScheduleProvider(old_client), NewScheduleProvider(new_client)
    )

    assert migrator.old_schedule_provider.get_schedule(old_schedule_name) == None
    assert migrator.new_schedule_provider.get_schedule(new_schedule_name) == ORIGINAL_SCHEDULE

    with pytest.raises(SystemExit) as e:
        migrator.migrate_schedule("my-job", "dev")

    assert "New schedule is already activated. Aborting." in capsys.readouterr().err


@mock_aws
def test_migrate_succeeds_if_new_schedule_already_active_but_with_different_cron(capsys):
    DEFAULT_SCHEDULE = "rate(5 minutes)"
    ORIGINAL_SCHEDULE = "rate(10 minutes)"

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
        ScheduleExpression=DEFAULT_SCHEDULE,
        State="ENABLED",
    )
    old_client.put_rule(
        Name=old_schedule_name,
        ScheduleExpression=ORIGINAL_SCHEDULE,
        State="DISABLED",
        Tags=[
            {"Key": "copilot-application", "Value": "demodjango"},
            {"Key": "copilot-environment", "Value": "dev"},
            {"Key": "copilot-service", "Value": "my-job"},
        ],
    )

    migrator = ScheduleMigrator(
        "demodjango", OldScheduleProvider(old_client), NewScheduleProvider(new_client)
    )

    assert migrator.old_schedule_provider.get_schedule(old_schedule_name) == None
    assert migrator.new_schedule_provider.get_schedule(new_schedule_name) == DEFAULT_SCHEDULE

    migrator.migrate_schedule("my-job", "dev")

    assert migrator.old_schedule_provider.get_schedule(old_schedule_name) == None
    assert migrator.new_schedule_provider.get_schedule(new_schedule_name) == ORIGINAL_SCHEDULE
