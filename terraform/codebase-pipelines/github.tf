resource "github_actions_variable" "ecr_repo" {
  for_each      = toset(var.use_github_actions ? [""] : [])
  repository    = var.repository
  variable_name = "ECR_REPO"
  value         = aws_ecr_repository.this.name
}

resource "github_actions_variable" "build_project" {
  for_each      = toset(var.requires_image_build && var.use_github_actions ? [""] : [])
  repository    = var.repository
  variable_name = "BUILD_PROJECT"
  value         = aws_codebuild_project.codebase_image_build[""].name
}

resource "github_actions_variable" "deploy_repo" {
  for_each      = toset(var.use_github_actions ? [""] : [])
  repository    = var.repository
  variable_name = "DEPLOY_REPO"
  value         = var.deploy_repository
}

resource "github_actions_variable" "platform_tools_version" {
  for_each      = toset(var.use_github_actions ? [""] : [])
  repository    = var.repository
  variable_name = "PLATFORM_TOOLS_VERSION"
  value         = var.platform_tools_version
}

resource "github_actions_secret" "oidc_role_arn_non_prod" {
  for_each    = toset(var.use_github_actions ? [""] : [])
  repository  = var.repository
  secret_name = "OIDC_ROLE_ARN_NON_PROD"
  value       = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-github-platform-non-prod"
}

resource "github_actions_secret" "oidc_role_arn_prod" {
  for_each    = toset(var.use_github_actions ? [""] : [])
  repository  = var.repository
  secret_name = "OIDC_ROLE_ARN"
  value       = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-github-platform-prod"
}

# TODO - teams are created in the SRE terraform-github repo, how can we ensure this slug matches?
# data "github_team" "team" {
#   # slug = "${var.application}-approvers"
#   slug = "platform"
# }

resource "github_repository_environment" "github_environments" {
  for_each          = toset(var.use_github_actions ? keys(var.env_config) : [])
  repository        = var.repository
  environment       = each.key
  can_admins_bypass = false

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = each.key == "prod"
  }

  # TODO - see comment above, need to match github team
  # dynamic "reviewers" {
  #   for_each = each.key == "prod" ? [""] : []
  #   content {
  #     teams = [data.github_team.team.id]
  #   }
  # }
}

resource "github_repository_environment_deployment_policy" "deploy_prod_policy" {
  for_each    = toset(var.use_github_actions ? [""] : [])
  repository  = var.repository
  environment = github_repository_environment.github_environments["prod"].environment
  tag_pattern = "*"
}
