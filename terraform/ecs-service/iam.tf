data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

resource "aws_iam_role" "ecs_task_execution_role" {
  name               = "${local.service_name}-ecs-task-execution-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role_policy.json
  tags               = local.tags
}

data "aws_iam_policy_document" "assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "secrets_role_policy" {
  count = var.service_config.secrets == null ? 0 : 1

  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.secrets_policy[count.index].arn
}

resource "aws_iam_policy" "secrets_policy" {
  count = var.service_config.secrets == null ? 0 : 1

  name        = "${local.service_name}-secrets-policy"
  description = "Allow application to access secrets manager"
  policy      = data.aws_iam_policy_document.secrets_policy[count.index].json
  tags        = local.tags
}

data "aws_iam_policy_document" "secrets_policy" {
  count = var.service_config.secrets == null ? 0 : 1

  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = [
      for secret in local.secrets : "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${secret}"
    ]
    condition {
      test = "StringEquals"
      # TODO - Consider changing condition when creating the new 'platform-helper secrets update' command
      variable = "ssm:ResourceTag/copilot-environment"
      values   = [var.environment]
    }
    condition {
      test = "StringEquals"
      # TODO - Consider changing condition when creating the new 'platform-helper secrets update' command
      variable = "aws:ResourceTag/copilot-application"
      values   = [var.application]
    }
  }

  statement {
    effect = "Allow"
    actions = [
      "kms:Decrypt"
    ]
    resources = [
      # TODO - Part of the `secrets update` command we should restrict the KMS key permissions
      "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:key/*"
    ]
  }
  statement {
    effect = "Allow"
    actions = [
      "kms:Decrypt"
    ]
    resources = [
      # TODO - Part of the `secrets update` command we should restrict the KMS key permissions
      "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:key/*"
    ]
    condition {
      test = "StringEquals"
      # TODO - Consider changing condition when creating the new 'platform-helper secrets update' command
      variable = "ssm:ResourceTag/copilot-environment"
      values   = [var.environment]
    }
    condition {
      test = "StringEquals"
      # TODO - Consider changing condition when creating the new 'platform-helper secrets update' command
      variable = "aws:ResourceTag/copilot-application"
      values   = [var.application]
    }
  }

  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameters"
    ]
    resources = [
      for variable in local.secrets : "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/${variable}"
    ]
    condition {
      test     = "StringEquals"
      variable = "ssm:ResourceTag/copilot-environment"
      values   = [var.environment]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/copilot-application"
      values   = [var.application]
    }
  }

  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameters"
    ]
    resources = [
      "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/*"
    ]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/copilot-application"
      values   = ["__all__"]
    }
  }
}

resource "aws_iam_role" "ecs_task_role" {
  name               = "${local.service_name}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role_policy.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "execute_command_policy" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.execute_command_policy.arn
}

resource "aws_iam_policy" "execute_command_policy" {
  name        = "${local.service_name}-execute-command-policy"
  description = ""
  policy      = data.aws_iam_policy_document.execute_command_policy.json
  tags        = local.tags
}

data "aws_iam_policy_document" "execute_command_policy" {

  # Needs 'resources = ["*"]' permission because the SSM agent running inside the conduit ECS task communicates with Amazon Message Gateway Service via ssmmessages actions.
  # See https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonmessagegatewayservice.html#amazonmessagegatewayservice-resources-for-iam-policies
  statement {
    effect = "Allow"
    actions = [
      "ssmmessages:CreateControlChannel",
      "ssmmessages:OpenControlChannel",
      "ssmmessages:CreateDataChannel",
      "ssmmessages:OpenDataChannel"
    ]
    resources = [
      "*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:${aws_cloudwatch_log_group.ecs_service_logs.name}"
    ]
  }

  statement {
    effect = "Deny"
    actions = [
      "iam:*",
    ]
    resources = [
      "*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "sts:AssumeRole",
    ]
    resources = [
      "arn:aws:iam::763451185160:role/AppConfigIpFilterRole"
    ]
  }
}
