variable "application" {
  type = string
}

variable "environment" {
  type = string
}

variable "env_config" {
  type = any
}

variable "platform_extensions" {
  type = any
}

variable "custom_iam_policy_json" {
  type    = string
  default = null

  validation {
    condition     = var.custom_iam_policy_json == null ? true : length(var.custom_iam_policy_json) <= 6144
    error_message = "The length of the custom IAM policy exceeds the 6144 character limit for IAM managed policies."
  }
}

variable "service_config" {
  type = object({
    name = string
    type = string

    http = optional(object({
      path             = string
      target_container = string
      healthcheck = optional(object({
        path                = optional(string)
        port                = optional(number)
        success_codes       = optional(string)
        healthy_threshold   = optional(number)
        unhealthy_threshold = optional(number)
        interval            = optional(string)
        timeout             = optional(string)
        grace_period        = optional(string)
      }))
    }))

    sidecars = optional(map(object({
      port      = number
      image     = string
      essential = optional(bool)
      variables = optional(map(string))
      secrets   = optional(map(string))
    })))

    image = object({
      location   = string
      port       = optional(number)
      depends_on = optional(map(string))
    })

    cpu        = number
    memory     = number
    count      = number
    exec       = optional(bool)
    entrypoint = optional(list(string))
    essential  = optional(bool)

    network = optional(object({
      connect = optional(bool)
      vpc = optional(object({
        placement = optional(string)
      }))
    }))

    storage = optional(object({
      readonly_fs          = optional(bool)
      writable_directories = optional(list(string))
    }))

    variables = optional(map(any))
    secrets   = optional(map(string))
  })
}
