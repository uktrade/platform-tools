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

variable "repository" {
  type = string
  default = null
}
