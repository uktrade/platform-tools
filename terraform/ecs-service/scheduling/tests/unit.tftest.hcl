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
  target = data.aws_iam_policy_document.start_ecs_task
  values = {
    json = "{\"Sid\": \"PlaceholderPolicyDoesNotMatter\"}"
  }
}

# override_data {
#   target = data.aws_iam_policy_document.service_logs
#   values = {
#     json = "{\"Sid\": \"PlaceholderPolicyDoesNotMatter\"}"
#   }
# }

# override_data {
#   target = data.aws_ssm_parameter.log-destination-arn
#   values = {
#     value = "{\"dev\":\"arn:aws:logs:eu-west-2:001122334455:log-group:/central/dev\",\"prod\":\"arn:aws:logs:eu-west-2:001122334455:log-group:/central/prod\"}"
#   }
# }


variables {
  name                = "db-dump"
  schedule            = "none"
  vpc_id              = "my-vpc"
  task_definition_arn = "arn:aws:logs:eu-west-2:001122334455:task-definition/my-app-dev-db-dump:7"
  cluster_id          = "my-cluster"
  subnet_ids          = ["subnet-0000001111122222c", "subnet-0000002222233333e"]
  tags                = {}
}

/* 
EventBridge test ideas:
- state machine target is correct
- IAM role is correct
*/

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

/*
State Machine tests:
- retries set to null result in no 'Retry' block
*/
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

/* 
ECS tests:
- platform (cpu architecture)
- ephemeral storage
- volumes

More generally - how do we handle testing shared functionality in both ecs-service and ecs-scheduled-job?
- Duplicating all tests that are relevant from ecs-service to ecs-scheduled-job?
- Splitting out shared module functionality into a 3rd module, and then having ecs-service and ecs-scheduled-job call the 3rd module? The 3rd module owns all the shared tests 
 */

# run "test_ecs_task_default_platform_is_x86_64" {
#   command = plan

#   assert {
#     condition     = local.cpu_architecture == "X86_64"
#     error_message = "Should be 'X86_64'"
#   }
# }

# run "test_ecs_task_platform_is_arm64" {
#   command = plan

#   variables {
#     service_config = merge(var.service_config, { platform = "arm64" })
#   }

#   assert {
#     condition     = local.cpu_architecture == "ARM64"
#     error_message = "Should be 'ARM64'"
#   }
# }