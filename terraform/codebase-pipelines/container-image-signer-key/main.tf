data "aws_caller_identity" "current" {}

locals {
  static_signer_alias = "alias/${var.application}-container-image-signer-key"

  default_key_alias_mappings = {
    v_15_08_2026 = {
      alias       = local.static_signer_alias
      description = "ECC_NIST_P256 Asymmetric KMS Key for image signing and verification"
    }
  }

  key_alias_mappings = var.key_alias_mappings != null ? var.key_alias_mappings : local.default_key_alias_mappings

  default_tags = {
    application         = var.application
    copilot-application = var.application
    managed-by          = "DBT Platform - Terraform"
  }
  tags = var.tags != null ? var.tags : local.default_tags

  base_env_config = {
    for name, config in var.env_config : name => {
      account_id = lookup(
        lookup(
          lookup(merge(lookup(var.env_config, "*", {}), config), "accounts", {}),
          "deploy",
          {},
        ),
        "id",
        {},
      )
    } if name != "*"
  }

  default_deploy_account_ids = distinct([for env in local.base_env_config : env.account_id])
  deploy_account_ids         = var.deploy_account_ids != null ? var.deploy_account_ids : local.default_deploy_account_ids
}

resource "aws_kms_key" "container_image_signer_key" {
  for_each = local.key_alias_mappings

  description              = each.value.description
  tags                     = local.tags
  customer_master_key_spec = "ECC_NIST_P256"
  key_usage                = "SIGN_VERIFY"
  enable_key_rotation      = false
  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "container-image-signing-key-policy"

    Statement = [
      {
        Sid    = "Enable IAM policies in the owning account"
        Effect = "Allow"

        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }

        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow deployment roles to verify signatures"
        Effect = "Allow"

        Principal = {
          AWS = [
            for account_id in local.deploy_account_ids :
            "arn:aws:iam::${account_id}:role/github-oidc-${var.application}-repo-role"
          ]
        }

        Action = [
          "kms:Verify",
          "kms:GetPublicKey",
          "kms:DescribeKey",
        ]

        Resource = "*"
      },
      {
        Sid    = "Allow the image build role to sign"
        Effect = "Allow"

        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/github-oidc-${var.application}-platform-image-build"
        }

        Action = [
          "kms:Sign",
          "kms:GetPublicKey",
          "kms:DescribeKey",
        ]

        Resource = "*"
      },
    ]
  })
}

resource "aws_kms_alias" "container_image_signer_key" {
  for_each      = local.key_alias_mappings
  name          = each.value.alias
  target_key_id = aws_kms_key.container_image_signer_key[each.key].key_id

  lifecycle {
    prevent_destroy = true
  }
}
