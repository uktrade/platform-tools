variable "application" {
  type = string
}

variable "codebase" {
  type = string
}

variable "repository" {
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
          invalidate_cache = optional(object({
            before = optional(list(string))
            after = optional(list(string))
            paths = string
          }))
        }
      ))
    }
  ))
}

variable "services" {
  type = any
}

variable "slack_channel" {
  type    = string
  default = "/codebuild/slack_oauth_channel"
}

variable "env_config" {
  type = any
}

variable "requires_image_build" {
  type    = bool
  default = true
}
