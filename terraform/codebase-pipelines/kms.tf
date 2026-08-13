resource "aws_kms_key" "image_sign_and_verify_key" {
  description = "KMS Key for image signing and verification"
  tags        = local.tags

  # policy = jsonencode({
  #   Statement = [
  #     {
  #       "Sid" : "Enable IAM User Permissions",
  #       "Effect" : "Allow",
  #       "Principal" : {
  #         "AWS" : [for id in local.deploy_account_ids : "arn:aws:iam::${id}:root"]
  #       },
  #       "Action" : "kms:*",
  #       "Resource" : "*"
  #     }
  #   ]
  #   Version = "2012-10-17"
  # })
}