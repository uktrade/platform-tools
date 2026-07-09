variable "application" {
  type = string
}

variable "pipeline_mode" {
  type        = string
  default     = "aws_codepipeline"
  description = "Controls which pipeline tool is used for ECS deployments."

  validation {
    condition     = contains(["aws_codepipeline", "dual_codepipeline_github", "github_actions"], var.pipeline_mode)
    error_message = "pipeline_mode must be one of 'aws_codepipeline', 'dual_codepipeline_github', or 'github_actions'"
  }
}

variable "requires_image_build" {
  type        = bool
  default     = true
  description = "Controls whether to create ci-image-builder CodeBuild project and related resources."
}

variable "codebase" {
  type = string
}

variable "repository" {
  type = string
}

variable "platform_tools_version" {
  type = string
}

variable "deploy_repository" {
  type    = string
  default = null
}

variable "deploy_repository_branch" {
  type    = string
  default = "main"
}

variable "additional_ecr_repository" {
  type    = string
  default = null
}

variable "cache_invalidation" {
  type = object({
    domains = map(object({
      paths       = list(string)
      environment = string
    }))
  })
}


variable "pipelines" {
  type = list(object(
    {
      name   = string
      branch = optional(string)
      tag    = optional(bool)

      environments = list(object(
        {
          name              = string
          requires_approval = optional(bool)
        }
      ))
    }
  ))
}

variable "services" {
  type     = any
  nullable = true
  default  = null

  validation {
    condition     = var.services != null || var.pipeline_mode == "github_actions"
    error_message = "Unless pipeline_mode is set to 'github_actions', you must define either a list of services or a list of run groups, each containing a list of services."
  }
}

variable "slack_channel" {
  type    = string
  default = "/codebuild/slack_oauth_channel"
}

variable "env_config" {
  type = any
}

variable "has_custom_pre_deploy" {
  type    = bool
  default = false

  # TODO - https://uktrade.atlassian.net/browse/DBTP-3132 to look into disabling AWS CodePipeline when custom pre/post deploy actions are present
  validation {
    condition     = var.pipeline_mode != "github_actions" || !var.has_custom_pre_deploy
    error_message = "Cannot set pipeline_mode as 'github_actions' due to the presence of custom pre-deploy actions which are not currently supported by platform tooling in GitHub Actions"
  }
}

variable "has_custom_post_deploy" {
  type    = bool
  default = false

  # TODO - https://uktrade.atlassian.net/browse/DBTP-3132 to look into disabling AWS CodePipeline when custom pre/post deploy actions are present
  validation {
    condition     = var.pipeline_mode != "github_actions" || !var.has_custom_post_deploy
    error_message = "Cannot set pipeline_mode as 'github_actions' due to the presence of custom post-deploy actions which are not currently supported by platform tooling in GitHub Actions"
  }
}

