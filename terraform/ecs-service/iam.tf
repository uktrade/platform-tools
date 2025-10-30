data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task_execution_role" {
  name               = "${local.full_service_name}-task-exec"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy_attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "secrets_role_policy_attachment" {
  count = var.service_config.secrets == null ? 0 : 1

  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.secrets_policy[count.index].arn
}

resource "aws_iam_policy" "secrets_policy" {
  count = var.service_config.secrets == null ? 0 : 1

  name        = "${local.full_service_name}-secrets-policy"
  description = "Allow application to access secrets manager"
  policy      = data.aws_iam_policy_document.secrets[count.index].json
  tags        = local.tags
}

data "aws_iam_policy_document" "secrets" {
  count = var.service_config.secrets == null ? 0 : 1

  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = [
      "arn:aws:secretsmanager:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:secret:*"
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
      "arn:aws:kms:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:key/*"
    ]
  }
  statement {
    effect = "Allow"
    actions = [
      "kms:Decrypt"
    ]
    resources = [
      # TODO - Part of the `secrets update` command we should restrict the KMS key permissions
      "arn:aws:kms:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:key/*"
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
      "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter/*"
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
      "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter/*"
    ]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/copilot-application"
      values   = ["__all__"]
    }
  }
}

resource "aws_iam_role" "ecs_task_role" {
  name               = "${local.full_service_name}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "execute_command_policy_attachment" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.execute_command_policy.arn
}

resource "aws_iam_policy" "execute_command_policy" {
  name        = "${local.full_service_name}-execute-command-policy"
  description = "Allows SSM agent access to ECS service. Required by the platform-helper conduit command. "
  policy      = data.aws_iam_policy_document.execute_command.json
  tags        = local.tags
}

data "aws_iam_policy_document" "execute_command" {

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
    effect = "Deny"
    actions = [
      "iam:*",
    ]
    resources = [
      "*"
    ]
  }
}

resource "aws_iam_role_policy_attachment" "service_logs_policy_attachment" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.service_logs_policy.arn
}

resource "aws_iam_policy" "service_logs_policy" {
  name        = "${local.full_service_name}-service-logs-policy"
  description = "Allows ECS service access to Cloudwatch logs"
  policy      = data.aws_iam_policy_document.service_logs.json
  tags        = local.tags
}

data "aws_iam_policy_document" "service_logs" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams"
    ]
    resources = [
      "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${aws_cloudwatch_log_group.ecs_service_logs.name}",
      "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${aws_cloudwatch_log_group.ecs_service_logs.name}:log-stream:*"
    ]
  }
}

resource "aws_iam_role_policy_attachment" "appconfig_policy_attachment" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.appconfig_policy.arn
}

resource "aws_iam_policy" "appconfig_policy" {
  name        = "${local.full_service_name}-appconfig-policy"
  description = "Allows the ECS service to assume the AppConfig role from the tooling account. Required for ip-filter."
  policy      = data.aws_iam_policy_document.appconfig.json
  tags        = local.tags
}

data "aws_iam_policy_document" "appconfig" {
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

resource "aws_iam_policy" "custom_iam_policy" {
  count       = var.custom_iam_policy_json != null ? 1 : 0
  name        = "${local.full_service_name}-custom-iam-policy"
  description = "Optional policy for custom permissions needed by the ECS task role of a service"
  policy      = var.custom_iam_policy_json
  tags        = local.tags
}

resource "aws_iam_role_policy_attachment" "custom_iam_policy_attachment" {
  count      = var.custom_iam_policy_json != null ? 1 : 0
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.custom_iam_policy[0].arn
}

##############################
# S3 EXTENSIONS — SAME ACCOUNT
##############################

resource "aws_iam_role_policy_attachment" "s3_same_account_policy_attachment" {
  for_each   = aws_iam_policy.s3_same_account_policy
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = each.value.arn
}

resource "aws_iam_policy" "s3_same_account_policy" {
  for_each    = local.s3_same_account_policy_objects
  name        = "${var.application}-${var.environment}-${var.service_config.name}-${each.key}-s3-policy"
  description = "S3 access for ${var.service_config.name} to extension ${each.key}"
  policy      = jsonencode(each.value)
  tags        = local.tags
}

# Resolve KMS key ARN using its alias. No alias --> no KMS key ARN --> no IAM policy statement for that KMS key.
data "aws_kms_alias" "s3_key" {
  for_each = local.s3_kms_alias_for_s3_extension
  name     = each.value
}

locals {
  kms_arn_for_s3_extension = {
    for name, value in local.s3_extensions_for_service_with_env_merged :
    name => (
      contains(keys(local.s3_kms_alias_for_s3_extension), name)
      ? try(data.aws_kms_alias.s3_key[name].target_key_arn, null)
      : null
    )
  }
}

locals {
  s3_same_account_policy_objects = {
    for name, conf in local.s3_extensions_for_service_with_env_merged :
    name => {
      Version = "2012-10-17"
      Statement = concat(
        # KMS statement only gets added if an ARN for that KMS key is found
        local.kms_arn_for_s3_extension[name] != null ? [
          {
            Sid      = "KMSDecryptAndGenerate"
            Effect   = "Allow"
            Action   = ["kms:Decrypt", "kms:GenerateDataKey"]
            Resource = [local.kms_arn_for_s3_extension[name]]
          }
        ] : [],
        [
          {
            Sid      = "S3ObjectActions"
            Effect   = "Allow"
            Action   = try(conf.readonly, false) ? ["s3:GetObject"] : ["s3:*Object"]
            Resource = ["arn:aws:s3:::${local.s3_bucket_name[name]}/*"]
          },
          {
            Sid      = "S3ListAction"
            Effect   = "Allow"
            Action   = ["s3:ListBucket"]
            Resource = ["arn:aws:s3:::${local.s3_bucket_name[name]}"]
          }
        ]
      )
    }
  }
}


###########################
# S3 EXTENSIONS — CROSS-ENV
###########################

resource "aws_iam_role_policy_attachment" "s3_cross_env_policy_attachment" {
  for_each   = aws_iam_policy.s3_cross_env_policy
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = each.value.arn
}

resource "aws_iam_policy" "s3_cross_env_policy" {
  for_each    = local.s3_cross_env_policy_objects
  name        = "${var.application}-${var.environment}-${var.service_config.name}-${replace(each.key, ":", "-")}-s3-policy-cross-env"
  description = "Cross environment S3 access for ${var.service_config.name} ${each.key}"
  policy      = jsonencode(each.value)
  tags        = local.tags
}

locals {
  s3_cross_env_policy_objects = {
    for key, rule in local.s3_cross_env_rules_for_this_service :
    key => {
      Version = "2012-10-17"
      Statement = concat(
        rule.is_static ? [] : [
          {
            Sid      = "KMSDecryptAndGenerate"
            Effect   = "Allow"
            Action   = ["kms:Decrypt", "kms:GenerateDataKey"]
            Resource = ["arn:aws:kms:${data.aws_region.current.region}:${rule.bucket_account}:key/*"]
            Condition = {
              StringEquals = {
                "aws:PrincipalTag/environment" = rule.service_env
              }
            }
          }
        ],
        [
          {
            Sid    = "S3ObjectActions"
            Effect = "Allow"
            Action = concat(
              try(rule.read, true) ? ["s3:Get*"] : [],
              try(rule.write, false) ? ["s3:Put*"] : []
            )
            Resource = ["arn:aws:s3:::${rule.bucket_name}/*"]
            Condition = {
              StringEquals = {
                "aws:PrincipalTag/environment" = rule.service_env
              }
            }
          },
          {
            Sid      = "S3ListAction"
            Effect   = "Allow"
            Action   = ["s3:ListBucket"]
            Resource = ["arn:aws:s3:::${rule.bucket_name}"]
            Condition = {
              StringEquals = {
                "aws:PrincipalTag/environment" = rule.service_env
              }
            }
          }
        ]
      )
    }
  }
}
