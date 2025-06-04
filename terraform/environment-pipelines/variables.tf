variable "application" {
  type = string
}

variable "deploy_repository_branch" {
  type    = string
  default = "main"
}

variable "environments" {
  type = map(
    object(
      {
        vpc               = optional(string)
        requires_approval = optional(bool)
      }
    )
  )
}

variable "env_config" {
  type = any
}

variable "pipeline_name" {
  type = string
}

variable "deploy_repository" {
  type = string
}

variable "slack_channel" {
  type    = string
  default = "/codebuild/slack_pipeline_notifications_channel"
}

variable "trigger_on_push" {
  type    = bool
  default = true
}

