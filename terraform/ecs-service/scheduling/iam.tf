### EventBridge
data "aws_iam_policy_document" "eventbridge_scheduler_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eventbridge_scheduler_role" {
  name               = "${var.name}-eb-scheduler"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_scheduler_assume_role.json
  tags               = var.tags
}

resource "aws_iam_policy" "eventbridge_execution_policy" {
  name        = "${var.name}-eb"
  description = "Allows EventBridge Schedule to start Scheduled Job State Machine execution."
  policy      = data.aws_iam_policy_document.eventbridge_permissions.json
  tags        = var.tags
}

data "aws_iam_policy_document" "eventbridge_permissions" {

  statement {
    effect = "Allow"
    actions = [
      "states:StartExecution"
    ]
    resources = [
      aws_sfn_state_machine.this.arn
    ]
  }
}

resource "aws_iam_role_policy_attachment" "eventbridge_execution_policy" {
  role       = aws_iam_role.eventbridge_scheduler_role.name
  policy_arn = aws_iam_policy.eventbridge_execution_policy.arn
}

### State Machine
data "aws_iam_policy_document" "state_machine_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:states:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:stateMachine:*"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "state_machine_role" {
  name               = "${var.name}-sm"
  assume_role_policy = data.aws_iam_policy_document.state_machine_assume_role.json
  tags               = var.tags
}

resource "aws_iam_policy" "state_machine_policy" {
  name        = "${var.name}-sm"
  description = "Allows the State Machine to interact with an ECS task and send logs"
  policy      = data.aws_iam_policy_document.state_machine_permissions.json
  tags        = var.tags
}

data "aws_iam_policy_document" "state_machine_permissions" {
  # checkov:skip=CKV_AWS_111: Fix is tracked in DBTP-3234.
  # checkov:skip=CKV_AWS_356: Fix is tracked in DBTP-3234.

  statement {
    effect = "Allow"
    actions = [
      "ecs:RunTask"
    ]
    resources = [
      var.task_definition_arn
    ]
  }
  statement {
    effect = "Allow"
    actions = [
      "ecs:StopTask",
      "ecs:DescribeTasks"
    ]
    resources = [
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:task/${local.cluster_name}/*"
    ]
  }
  statement {
    effect = "Allow"
    actions = [
      "events:PutTargets",
      "events:PutRule",
      "events:DescribeRule"
    ]
    resources = [
      "arn:aws:events:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:rule/StepFunctionsGetEventsForECSTaskRule"
    ]
  }
  statement {
    effect = "Allow"
    actions = [
      "iam:PassRole",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.full_service_name}-task-exec",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.full_service_name}-ecs-task"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogDelivery",
      "logs:CreateLogStream",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutLogEvents",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups"
    ]

    resources = ["*"]
  }
}

resource "aws_iam_role_policy_attachment" "state_machine_policy" {
  role       = aws_iam_role.state_machine_role.name
  policy_arn = aws_iam_policy.state_machine_policy.arn
}
