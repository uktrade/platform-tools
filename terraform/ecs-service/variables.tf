variable "application" {
  type = string
}

variable "environment" {
  type = string
}

variable "service_config" {
  type = object({
    name = string
    type = string
    http = object({
      path             = string
      target_container = string
      healthcheck = optional(object({
        path                = optional(string)
        port                = optional(string)
        success_codes       = optional(string)
        healthy_threshold   = optional(string)
        unhealthy_threshold = optional(string)
        interval            = optional(string)
        timeout             = optional(string)
        grace_period        = optional(string)
      }))
    })
  })
}

variable "vpc_name" {
  type    = string
  default = "platform-sandbox-dev" #TODO - Remove hardcoding
}

