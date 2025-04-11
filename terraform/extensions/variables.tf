variable "args" {
  type = object({
    application = string,
    extensions  = any,
    services    = any,
    env_config  = any
  })
}

variable "environment" {
  type = string
}
