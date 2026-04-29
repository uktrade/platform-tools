variable "args" {
  type = object({
    application = string,
    services    = any,
    env_config  = any
  })
}

variable "environment" {
  type = string
}

variable "repos" {
  type     = list(string)
  default  = []
  nullable = false
}

variable "pinned_version" {
  type    = string
  default = null # Only populated for centralised services
}

variable "deploy_repository" {
  type = string
}
