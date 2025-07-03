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
  type    = list(string)
  default = null # Default to null in case the repository isn't provided in platform-config.yml
}

variable "service-deployment-mode" {
  type    = string
  default = "platform" #TODO - Remove this line once platform-helper changes are in place
}
