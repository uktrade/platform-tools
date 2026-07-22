### Eventbridge
resource "aws_scheduler_schedule" "this" {
  # checkov:skip=CKV_AWS_297: Fix is tracked in DBTP-3234.

  schedule_expression = var.schedule == "none" ? "rate(5 minutes)" : local.schedule_expression

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

}

resource "aws_security_group" "scheduled_job" {
  # checkov:skip=CKV2_AWS_5: This security group is in fact referenced by the state machine definition, but checkov does not inspect it that deeply.
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
  # checkov:skip=CKV_AWS_284: X-ray tracking not used on platform.
  name     = "${var.name}-sfn"
  role_arn = aws_iam_role.state_machine_role.arn

  definition = jsonencode(local.state_machine_definition)

  logging_configuration {
    log_destination        = "${var.log_group_arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
}
