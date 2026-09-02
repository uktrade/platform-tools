data "aws_caller_identity" "current" {}

resource "aws_kms_key" "container_image_signer_key" {
  for_each = var.key_alias_mappings

  description              = each.value.description
  tags                     = var.tags
  customer_master_key_spec = "ECC_NIST_P256"
  key_usage                = "SIGN_VERIFY"
  enable_key_rotation      = false
  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "key-default-1"
    Statement = [
      {
        Sid    = "Allow verifying with the key"
        Effect = "Allow"
        Principal = {
          AWS = [for id in var.deploy_account_ids : "arn:aws:iam::${id}:role/github-oidc-${var.application}-repo-role"]
        },
        Action = [
          "kms:Verify",
          "kms:GetPublicKey",
          "kms:DescribeKey"
        ],
        Resource = "*"
      },
      {
        Sid    = "Allow signing with the key"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/github-oidc-build-placeholder-role" //build oidc role
        },
        Action = [
          "kms:Sign",
          "kms:DescribeKey"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_kms_alias" "container_image_signer_key" {
  for_each      = var.key_alias_mappings
  name          = each.value.alias
  target_key_id = aws_kms_key.container_image_signer_key[each.key].key_id

  lifecycle {
    prevent_destroy = true
  }
}
