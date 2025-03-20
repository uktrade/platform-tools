resource "aws_ssm_parameter" "master-secret-arn" {
  # checkov:skip=CKV_AWS_337: Need to determine downstream impact before moving to CMK - raised as DBTP-1217
  name  = "/copilot/${var.application}/${var.environment}/secrets/${local.rds_master_secret_name}"
  type  = "SecureString"
  value = aws_db_instance.default.master_user_secret[0].secret_arn
  tags  = local.tags
}

