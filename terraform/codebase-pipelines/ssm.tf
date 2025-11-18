resource "aws_ssm_parameter" "codebase_config" {
  # checkov:skip=CKV2_AWS_34: AWS SSM Parameter doesn't need to be Encrypted
  # checkov:skip=CKV_AWS_337: AWS SSM Parameter doesn't need to be Encrypted
  name        = "/copilot/applications/${var.application}/codebases/${var.codebase}"
  description = "Configuration for the ${var.codebase} codebase, used by platform-helper commands"
  type        = "String"
  value = jsonencode({
    "name" : var.codebase,
    "repository" : var.repository,
    "deploy_repository_branch" : var.deploy_repository_branch,
    "additional_ecr_repository" : var.additional_ecr_repository,
    "slack_channel" : var.slack_channel,
    "requires_image_build" : var.requires_image_build,
    "services" : var.services,
    "pipelines" : var.pipelines
  })

  tags = local.tags
}

data "aws_ssm_parameter" "log-destination-arn" {
  name = "/copilot/tools/central_log_groups"
}