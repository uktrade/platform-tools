resource "aws_ssm_parameter" "platform_version" {
  # checkov:skip=CKV2_AWS_34: This AWS SSM Parameter doesn't need to be encrypted
  name  = local.parameter_name
  tier  = "Standard"
  type  = "String"
  value = var.platform_version
  tags  = local.tags
}
