### Eventbridge
resource "aws_scheduler_schedule" "this" {

  # Required
  # TODO: handle day-of-week and day-of-month wildcards, e.g. if day-of-week is specified, then day-of-month must be "?" ("?"" means "any") and vice-versa
  # TODO: add cron() around the cron expression in the service-config file, so "30 * * * ?" would be "cron(0 * * * ?)"
  # TODO: Add test for above logic - done
  # TODO: Add comment on cron gotchas in EventBridge Scheduler (when to use * and ? examples)
  schedule_expression = var.schedule == "none" ? "rate(5 minutes)" : "cron(${var.schedule})"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_sfn_state_machine.this.arn
    role_arn = aws_iam_role.eventbridge_scheduler_role.arn
  }

  # Optional
  name       = "${var.name}-schedule"
  group_name = "default"

  state = var.schedule == "none" ? "DISABLED" : "ENABLED"

  # retries? 
  #   retry_policy {
  #     maximum_event_age_in_seconds = 60
  #     maximum_retry_attempts = 1
  #   }

}

resource "aws_security_group" "scheduled_job" {
  name        = "${var.name}-scheduled-job"
  description = "SG for scheduled job ECS task"
  vpc_id      = var.vpc_id

  tags = var.tags
}

resource "aws_vpc_security_group_egress_rule" "scheduled_job_egress" {
  security_group_id = aws_security_group.scheduled_job.id
  description       = "Allow all outbound traffic"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"

  tags = var.tags
}

### State Machine
resource "aws_sfn_state_machine" "this" {
  name     = "${var.name}-sfn"
  role_arn = aws_iam_role.state_machine_role.arn

  definition = jsonencode(local.state_machine_definition)

  logging_configuration {
    log_destination        = "${var.log_group_arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
}
