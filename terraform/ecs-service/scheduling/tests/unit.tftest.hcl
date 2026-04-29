mock_provider "aws" {}

override_data {
  target = data.aws_caller_identity.current
  values = {
    account_id = "001122334455"
  }
}

override_data {
  target = data.aws_iam_policy_document.eventbridge_scheduler_assume_role
  values = {
    json = "{\"Sid\": \"PlaceholderPolicyDoesNotMatter\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.state_machine_assume_role
  values = {
    json = "{\"Sid\": \"PlaceholderPolicyDoesNotMatter\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.state_machine_permissions
  values = {
    json = "{\"Sid\": \"PlaceholderPolicyDoesNotMatter\"}"
  }
}

variables {
  name                = "my-app-dev-db-dump"
  schedule            = "none"
  vpc_id              = "vpc-12345678901234567"
  task_definition_arn = "arn:aws:logs:eu-west-2:001122334455:task-definition/my-app-dev-db-dump:7"
  cluster_id          = "arn:aws:ecs:eu-west-2:123456789012:cluster/my-cluster"
  subnet_ids          = ["subnet-0000001111122222c", "subnet-0000002222233333e"]
  tags                = {}
  log_group_arn       = "arn:aws:logs:eu-west-2:123456789012:log-group:/platform/ecs/service/my-app/dev/db-dump"
}

run "test_none_schedule_expression_is_disabled" {
  command = plan
  assert {
    condition     = aws_scheduler_schedule.this.state == "DISABLED"
    error_message = "Should be 'DISABLED'"
  }
}

run "test_rate_schedule_expression_is_enabled" {
  command = plan

  variables {
    schedule = "rate(5 minutes)"
  }

  assert {
    condition     = aws_scheduler_schedule.this.state == "ENABLED"
    error_message = "Should be 'ENABLED'"
  }
}

run "test_cron_schedule_expression_is_as_expected" {
  command = plan

  variables {
    schedule = "5 * * * ?"
  }

  assert {
    condition     = aws_scheduler_schedule.this.schedule_expression == "5 * * * ?"
    error_message = "Should be '5 * * * ?'"
  }

  assert {
    condition     = aws_scheduler_schedule.this.state == "ENABLED"
    error_message = "Should be 'ENABLED'"
  }
}

run "test_none_schedule_expression_defaults_to_rate_5_minutes" {
  command = plan

  assert {
    condition     = aws_scheduler_schedule.this.schedule_expression == "rate(5 minutes)"
    error_message = "Should be 'rate(5 minutes)'"
  }
}

run "test_state_machine_definition_has_no_retry" {
  command = plan

  assert {
    condition     = length(local.state_machine_definition.States.run-fargate-task.Retry) == 0
    error_message = "Should have a length of '0'"
  }
}

run "test_state_machine_definition_has_expected_retry" {
  command = plan

  variables {
    retries = 1
  }

  assert {
    condition     = local.state_machine_definition.States.run-fargate-task.Retry[0].MaxAttempts == 1
    error_message = "Should have MaxAttempts as '1'"
  }
}


run "test_state_machine_definition_has_no_timeout" {
  command = plan

  assert {
    condition     = local.state_machine_definition.TimeoutSeconds == 86400
    error_message = "Should have a timeout of 86400"
  }
}
