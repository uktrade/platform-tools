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
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.secrets_policy.arn
}

resource "aws_iam_policy" "secrets_policy" {
  name        = "${local.service_name}-secrets-policy"
  description = "Allow application to access secrets manager"
  policy      = data.aws_iam_policy_document.secrets_policy.json
}

data "aws_iam_policy_document" "secrets_policy" {
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
      for variable in local.secrets : "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/${variable}"
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
}

data "aws_iam_policy_document" "execute_command_policy" {
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
      "*"
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
      # TODO - Where does this arn come from, current added by platform-helper copilot make-addons?
      "arn:aws:iam::763451185160:role/AppConfigIpFilterRole"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "sts:AssumeRole",
    ]
    resources = [
      # TODO - Where does this arn come from, current added by platform-helper copilot make-addons?
      "arn:aws:iam::480224066791:role/amp-prometheus-role"
    ]
  }
}

# TODO as part of `platform-helper make-addons` replacement
# resource "aws_iam_role_policy_attachment" "bucket_access_policy" {
#   for_each   = local.bucket_access_services
#   role       = aws_iam_role.ecs_task_role[each.key].name
#   policy_arn = aws_iam_policy.bucket_access_policy[each.key].arn
# }
#
# resource "aws_iam_policy" "bucket_access_policy" {
#   for_each    = local.bucket_access_services
#   name        = "${local.cluster_name}-${each.key}-iam-permissions-policy"
#   description = ""
#   policy      = data.aws_iam_policy_document.bucket_access_policy[each.key].json
# }
#
# data "aws_iam_policy_document" "bucket_access_policy" {
#   for_each = local.bucket_access_services
#
#   statement {
#     effect = "Allow"
#     actions = [
#       "kms:Decrypt",
#       "kms:GenerateDataKey"
#     ]
#     resources = [
#       for bucket_key, bucket_config in var.s3_config : data.aws_kms_alias.bucket_key_alias[bucket_key].target_key_arn
#       if contains(bucket_config.services, each.key) && lookup(bucket_config, "serve_static_content", false) == false
#     ]
#   }
#
#   statement {
#     effect = "Allow"
#     actions = [
#       "s3:*Object",
#       "s3:ListBucket"
#     ]
#     resources = [
#       for bucket_key, bucket_config in var.s3_config : "arn:aws:s3:::${bucket_config.bucket_name}/*"
#       if contains(bucket_config.services, each.key)
#     ]
#   }
# }
#
# data "aws_kms_alias" "bucket_key_alias" {
#   for_each = { for bucket_key, bucket_config in var.s3_config : bucket_key => bucket_config if lookup(bucket_config, "serve_static_content", false) == false }
#   name     = "alias/${var.application}-${var.environment}-${each.value.bucket_name}-key"
# }