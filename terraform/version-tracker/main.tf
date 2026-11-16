resource "aws_ssm_parameter" "platform_version" {
  # checkov:skip=CKV2_AWS_34: This AWS SSM Parameter doesn't need to be encrypted
  name  = local.parameter_name
  tier  = "Standard"
  type  = "String"
  value = var.platform_version
  tags  = local.tags
  # The parameter's value is also stored in its description so that DataDog can automatically ingest it.
  # This powers dashboards like the versioning section of the Orchestration Observability dashboard.
  description = var.platform_version
}
