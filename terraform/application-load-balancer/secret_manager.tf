resource "aws_secretsmanager_secret" "origin-verify-secret" {
  for_each                = toset(local.cdn_enabled ? [""] : [])
  name                    = "${var.application}-${var.environment}-origin-verify-header-secret"
  description             = "Secret used for Origin verification in WAF rules"
  kms_key_id              = aws_kms_key.origin_verify_secret_key[""].key_id
  recovery_window_in_days = 0
  tags                    = local.tags
}

data "aws_iam_policy_document" "secret_manager_policy" {
  for_each = toset(local.cdn_enabled ? [""] : [])
  statement {
    sid    = "AllowAssumedRoleToAccessSecret"
    effect = "Allow"

    principals {
      type = "AWS"
      identifiers = [
        "arn:aws:iam::${var.dns_account_id}:role/environment-pipeline-assumed-role"
      ]
    }

    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ]

    resources = [aws_secretsmanager_secret.origin-verify-secret[""].arn]
  }
}

resource "aws_secretsmanager_secret_policy" "secret_policy" {
  for_each   = toset(local.cdn_enabled ? [""] : [])
  secret_arn = aws_secretsmanager_secret.origin-verify-secret[""].arn
  policy     = data.aws_iam_policy_document.secret_manager_policy[""].json
}

resource "aws_kms_key" "origin_verify_secret_key" {
  for_each                = toset(local.cdn_enabled ? [""] : [])
  description             = "KMS key for ${var.application}-${var.environment}-origin-verify-header-secret"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"

        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow Rotation Lambda Function to Use Key"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${var.environment}-origin-secret-rotate-role"
        }
        Action   = ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey"]
        Resource = "*"
      }
    ]
  })

  tags       = local.tags
  depends_on = [aws_iam_role.origin-secret-rotate-execution-role]
}

resource "aws_kms_alias" "origin_verify_secret_key_alias" {
  for_each      = toset(local.cdn_enabled ? [""] : [])
  name          = "alias/${var.application}-${var.environment}-origin-verify-header-secret-key"
  target_key_id = aws_kms_key.origin_verify_secret_key[""].key_id
}

# Secrets Manager Rotation Schedule
resource "aws_secretsmanager_secret_rotation" "origin-verify-rotate-schedule" {
  for_each            = toset(local.cdn_enabled ? [""] : [])
  secret_id           = aws_secretsmanager_secret.origin-verify-secret[""].id
  rotation_lambda_arn = aws_lambda_function.origin-secret-rotate-function[""].arn
  rotate_immediately  = true
  rotation_rules {
    automatically_after_days = 7
  }
}

# These moved blocks are to prevent resources being recreated
moved {
  from = aws_secretsmanager_secret.origin-verify-secret
  to   = aws_secretsmanager_secret.origin-verify-secret[""]
}

moved {
  from = aws_secretsmanager_secret_policy.secret_policy
  to   = aws_secretsmanager_secret_policy.secret_policy[""]
}

moved {
  from = aws_secretsmanager_secret_rotation.origin-verify-rotate-schedule
  to   = aws_secretsmanager_secret_rotation.origin-verify-rotate-schedule[""]
}

moved {
  from = aws_kms_key.origin_verify_secret_key
  to   = aws_kms_key.origin_verify_secret_key[""]
}

moved {
  from = aws_kms_alias.origin_verify_secret_key_alias
  to   = aws_kms_alias.origin_verify_secret_key_alias[""]
}
