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
  name               = "${var.name}-eventbridge-scheduler"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_scheduler_assume_role.json
  tags               = var.tags
}

resource "aws_iam_policy" "start_state_machine_execution_policy" {
  name        = "${var.name}-state-machine-policy"
  description = "Allows EventBridge Schedule to start Scheduled Job State Machine execution."
  policy      = data.aws_iam_policy_document.start_state_machine_execution.json
  tags        = var.tags
}

data "aws_iam_policy_document" "start_state_machine_execution" {

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

resource "aws_iam_role_policy_attachment" "eventbridge_scheduler_role" {
  role       = aws_iam_role.eventbridge_scheduler_role.name
  policy_arn = aws_iam_policy.start_state_machine_execution_policy.arn
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
  name               = "${var.name}-state-machine"
  assume_role_policy = data.aws_iam_policy_document.state_machine_assume_role.json
  tags               = var.tags
}

resource "aws_iam_policy" "start_ecs_task_policy" {
  name        = "${var.name}-start-task-policy"
  description = "Allows the State Machine to start an ECS task."
  policy      = data.aws_iam_policy_document.start_ecs_task.json
  tags        = var.tags
}

data "aws_iam_policy_document" "start_ecs_task" {

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
}

resource "aws_iam_role_policy_attachment" "state_machine_start_ecs_task" {
  role       = aws_iam_role.state_machine_role.name
  policy_arn = aws_iam_policy.start_ecs_task_policy.arn
}