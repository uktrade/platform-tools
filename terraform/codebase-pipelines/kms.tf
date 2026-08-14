resource "aws_kms_key" "image_sign_and_verify_key" {
  description              = "ECC_NIST_P256 Asymmetric KMS Key for image signing and verification"
  tags                     = local.tags
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
          AWS = [for id in local.deploy_account_ids : "arn:aws:iam::${id}:role/github-oidc-${var.application}-repo-role"]
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

resource "aws_kms_alias" "image_sign_and_verify_key" {
  name          = "alias/image-signing-key"
  target_key_id = aws_kms_key.image_sign_and_verify_key.key_id

  lifecycle {
    prevent_destroy = true
  }
}
